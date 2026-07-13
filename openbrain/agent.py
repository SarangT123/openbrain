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
    on_chunk: Optional[Callable[[str], None]] = None,
    on_tool_call: Optional[Callable[[dict], None]] = None,
) -> AgentResult:
    options = {"num_ctx": num_ctx, "num_predict": num_predict if num_predict > 0 else -1, "temperature": temperature}
    if seed != -1:
        options["seed"] = seed

    tool_iter = 0
    forced_retries_used = 0
    calc_streak = 0
    tool_calls_log: list[dict] = []

    ollama_messages = list(messages)

    while tool_iter < max_tool_iters:
        kwargs: dict = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": options,
            "keep_alive": keep_alive,
        }
        if tools:
            kwargs["tools"] = tools

        resp = await client.chat(**kwargs)

        tool_calls = resp.message.tool_calls or []

        if not tool_calls:
            if force_tool_use and tool_iter == 0 and forced_retries_used < force_tool_retry_limit:
                forced_retries_used += 1
                ollama_messages.append({
                    "role": "user",
                    "content": (
                        "You answered without calling any tool. Re-derive this "
                        "step by step, calling run_python or sympy_calc to verify "
                        "each step, before giving your final answer."
                    ),
                })
                tool_iter += 1
                continue
            return AgentResult(
                final_text=resp.message.content or "",
                tool_calls=tool_calls_log,
                iterations=tool_iter,
                model_used=model,
            )

        def _resolve_args(arg_val) -> dict:
            if isinstance(arg_val, dict):
                return arg_val
            if isinstance(arg_val, str):
                try:
                    return json.loads(arg_val)
                except json.JSONDecodeError:
                    return {}
            return {}

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
            "content": resp.message.content or "",
            "tool_calls": tool_calls_resolved,
        })

        for tc in tool_calls:
            fn = tc.function.name
            args = _resolve_args(tc.function.arguments)
            tool_calls_log.append({"name": fn, "args": args})
            if on_tool_call:
                on_tool_call({"name": fn})
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

        tool_iter += 1

    return AgentResult(
        final_text="[max tool iterations reached]",
        tool_calls=tool_calls_log,
        iterations=tool_iter,
        model_used=model,
    )