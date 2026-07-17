import asyncio
import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from ollama import AsyncClient

from openbrain.tools import TOOL_DISPATCH


@dataclass
class AgentResult:
    final_text: str
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    model_used: str = ""


def _resolve_args(arg_val) -> dict:
    if isinstance(arg_val, dict):
        return arg_val
    if isinstance(arg_val, str):
        try:
            return json.loads(arg_val)
        except json.JSONDecodeError:
            return {}
    return {}


async def run_agent_turn(
    client: AsyncClient,
    model: str,
    messages: list[dict],
    tools: list[dict],
    *,
    temperature: float = 0.15,
    seed: int = -1,
    num_ctx: int = 4096,
    num_predict: int = -1,
    keep_alive: str = "5m",
    max_tool_iters: int = 10,
    force_tool_use: bool = False,
    force_tool_retry_limit: int = 1,
    calc_guard_enabled: bool = False,
    calc_guard_threshold: int = 3,
    on_chunk: Optional[Callable[[str, str], None]] = None,
    on_tool_call: Optional[Callable[[dict], None]] = None,
    on_tool_result: Optional[Callable[[str, str], None]] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> AgentResult:
    options = {"num_ctx": num_ctx, "num_predict": num_predict if num_predict > 0 else -1, "temperature": temperature}
    if seed != -1:
        options["seed"] = seed

    tool_iter = 0
    forced_retries_used = 0
    calc_streak = 0
    tool_calls_log: list[dict] = []

    ollama_messages = list(messages)

    continuation = False

    while tool_iter < max_tool_iters:
        if not continuation:
            content_parts: list[str] = []
            thinking_parts: list[str] = []

        kwargs: dict = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": options,
            "keep_alive": keep_alive,
        }
        if tools:
            kwargs["tools"] = tools

        gen = await client.chat(**kwargs)

        new_tool_calls = None
        async for part in gen:
            if cancel_event and cancel_event.is_set():
                content_parts.append("\n\n*[Cancelled]*")
                break
            if part.message.tool_calls:
                new_tool_calls = part.message.tool_calls
            c_chunk = getattr(part.message, "content", None) or ""
            t_chunk = getattr(part.message, "thinking", None) or ""
            if c_chunk:
                content_parts.append(c_chunk)
            if t_chunk:
                thinking_parts.append(t_chunk)
            if (c_chunk or t_chunk) and on_chunk:
                on_chunk("".join(content_parts), "".join(thinking_parts))

        tool_calls = new_tool_calls or []

        if not tool_calls:
            if force_tool_use and tool_iter == 0 and forced_retries_used < force_tool_retry_limit:
                forced_retries_used += 1
                content = "".join(content_parts)
                # Fix #2: preserve the model's own answer before nudging
                ollama_messages.append({"role": "assistant", "content": content})
                ollama_messages.append({
                    "role": "user",
                    "content": (
                        "You answered without calling any tool. Re-derive this "
                        "step by step, calling run_python or sympy_calc to verify "
                        "each step, before giving your final answer."
                    ),
                })
                tool_iter += 1
                continuation = True
                continue
            return AgentResult(
                final_text="".join(content_parts),
                tool_calls=tool_calls_log,
                iterations=tool_iter + 1,
                model_used=model,
            )

        content = "".join(content_parts)

        tool_calls_resolved = [
            {
                "function": {
                    "name": tc.function.name,
                    "arguments": _resolve_args(tc.function.arguments),
                }
            }
            for tc in tool_calls
        ]

        ollama_messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls_resolved,
        })

        for tc in tool_calls:
            fn = tc.function.name
            args = _resolve_args(tc.function.arguments)
            tool_calls_log.append({"name": fn, "args": args})
            if on_tool_call:
                on_tool_call({"name": fn, "args": args})
            handler = TOOL_DISPATCH.get(fn)
            if fn == "calculate":
                calc_streak += 1
            elif fn in ("run_python", "sympy_calc"):
                calc_streak = 0
            result = (
                await handler(**args)
                if handler
                else f"Unknown tool: {fn}"
            )
            if on_tool_result:
                on_tool_result(fn, result)
            ollama_messages.append({
                "role": "tool",
                "content": result,
                "name": fn,
            })

        if calc_guard_enabled and calc_streak >= calc_guard_threshold:
            calc_streak = 0
            ollama_messages.append({
                "role": "user",
                "content": (
                    "You've used calculate several times without verifying with "
                    "run_python — brute-force or simulate this to confirm your "
                    "derivation."
                ),
            })

        continuation = False
        tool_iter += 1

    return AgentResult(
        final_text="[max tool iterations reached]",
        tool_calls=tool_calls_log,
        iterations=tool_iter,
        model_used=model,
    )
