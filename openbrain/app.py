import asyncio
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from ollama import AsyncClient, Client
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Label

from openbrain.config import DATA_DIR, load_config, save_config_to_disk
from openbrain.tools import TOOLS, TOOL_DISPATCH
from openbrain.screens.action import ActionScreen
from openbrain.screens.branch_select import BranchSelectScreen
from openbrain.screens.model_select import ModelSelectScreen
from openbrain.screens.session_list import SessionListScreen
from openbrain.screens.system_prompt import SystemPromptScreen
from openbrain.screens.template_select import TemplateSelectScreen
from openbrain.utils import (
    ModelConfig,
    copy_to_clipboard,
    format_image_info,
    image_path_to_base64,
    load_templates,
    make_message,
    read_image_from_clipboard,
)
from openbrain.widgets.chat_message import ChatMessage
from openbrain.widgets.context_bar import ContextBar


class OpenCodeTUI(App):
    TITLE: ClassVar[str] = "openbrain"
    SUB_TITLE: ClassVar[str] = "AI coding assistant"
    CSS = """
    Screen {
        background: #1e1e2e;
    }
    * {
        scrollbar-color: #45475a;
        scrollbar-color-hover: #585b70;
        scrollbar-color-active: #89b4fa;
    }
    Header {
        background: #181825;
        color: #cdd6f4;
    }
    Header > HeaderClock {
        color: #6c7086;
    }
    Header > HeaderTitle {
        color: #cdd6f4;
    }
    Footer {
        background: #181825;
        color: #6c7086;
    }
    Footer > FooterKey {
        color: #f5c2e7;
    }
    Footer > FooterSeparator {
        color: #313244;
    }
    Footer > FooterDescription {
        color: #a6adc8;
    }
    #chat-container {
        height: 1fr;
        overflow-y: auto;
        padding: 0 0;
        background: #1e1e2e;
    }
    #input-wrapper {
        dock: bottom;
        height: auto;
        background: #181825;
        layout: vertical;
    }
    #context-bar {
        height: 1;
        background: #181825;
    }
    #chat-input {
        background: #313244;
        color: #cdd6f4;
        border: none;
        padding: 0 2;
        height: 3;
    }
    #chat-input:focus {
        border: none;
    }
    #image-indicator {
        height: 1;
        background: #313244;
        color: #f9e2af;
        padding: 0 2;
        display: none;
    }
    #chat-input .textual-input-cursor {
        color: #f5c2e7;
    }
    ChatMessage {
        margin: 0 0 1 0;
        padding: 0 0 1 1;
        border-left: solid #585b70;
    }
    ChatMessage.user {
        background: #313244;
        border-left: solid #89b4fa;
    }
    ChatMessage.assistant {
        background: #1e1e2e;
        border-left: solid #a6e3a1;
    }
    #welcome {
        color: #585b70;
        text-align: center;
        margin-top: 3;
        background: #1e1e2e;
    }
    ActionScreen,
    ModelSelectScreen,
    SystemPromptScreen,
    BranchSelectScreen,
    SessionListScreen {
        background: #11111b;
    }
    ActionScreen > Container,
    ModelSelectScreen > Container,
    SystemPromptScreen > Container,
    BranchSelectScreen > Container,
    TemplateSelectScreen > Container,
    SessionListScreen > Container {
        background: #1e1e2e;
        border: thick #b4befe;
        padding: 1 2;
        width: 60;
        height: auto;
        margin-top: 2;
    }
    ModelSelectScreen .title,
    SystemPromptScreen .title,
    BranchSelectScreen .title,
    TemplateSelectScreen .title,
    ActionScreen .title,
    SessionListScreen .title {
        text-style: bold;
        color: #b4befe;
        padding-top: 1;
        padding-bottom: 0;
    }
    ModelSelectScreen .hint,
    SystemPromptScreen .hint,
    BranchSelectScreen .hint,
    TemplateSelectScreen .hint,
    ActionScreen .hint,
    SessionListScreen .hint {
        color: #6c7086;
        padding-top: 0;
    }
    ModelSelectScreen ListView,
    BranchSelectScreen ListView,
    TemplateSelectScreen ListView,
    ActionScreen ListView,
    SessionListScreen ListView {
        height: 8;
        border: none;
        background: #313244;
    }
    ModelSelectScreen ListView#ctx-list {
        height: 5;
    }
    SessionListScreen ListView#session-list {
        height: 12;
    }
    ModelSelectScreen ListItem,
    BranchSelectScreen ListItem,
    TemplateSelectScreen ListItem,
    ActionScreen ListItem,
    SessionListScreen ListItem {
        background: #313244;
        color: #cdd6f4;
        padding: 0 1;
    }
    ModelSelectScreen ListItem:hover,
    BranchSelectScreen ListItem:hover,
    TemplateSelectScreen ListItem:hover,
    ActionScreen ListItem:hover,
    SessionListScreen ListItem:hover {
        background: #45475a;
    }
    ModelSelectScreen ListView:focus > ListItem:hover,
    BranchSelectScreen ListView:focus > ListItem:hover,
    TemplateSelectScreen ListView:focus > ListItem:hover,
    ActionScreen ListView:focus > ListItem:hover,
    SessionListScreen ListView:focus > ListItem:hover {
        background: #585b70;
    }
    ModelSelectScreen ListView > ListItem:focus,
    BranchSelectScreen ListView > ListItem:focus,
    TemplateSelectScreen ListView > ListItem:focus,
    ActionScreen ListView > ListItem:focus,
    SessionListScreen ListView > ListItem:focus {
        background: #45475a;
    }
    ModelSelectScreen Input {
        background: #313244;
        color: #cdd6f4;
        margin-bottom: 0;
    }
    ModelSelectScreen Input:focus {
        border: none;
    }
    SystemPromptScreen TextArea {
        background: #313244;
        color: #cdd6f4;
        border: none;
        height: 12;
        margin: 1 0;
    }
    SystemPromptScreen TextArea:focus {
        border: none;
    }
    SystemPromptScreen TextArea > TextAreaCursor {
        color: #f5c2e7;
    }
    SystemPromptScreen TextArea > TextAreaSelection {
        background: #585b70;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+m", "change_model", "Model"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+k", "cancel_stream", "Cancel", show=False),
        Binding("ctrl+p", "action_screen", "Actions", priority=True),
        Binding("ctrl+y", "copy_last", "Copy"),
        Binding("ctrl+up", "edit_last", "Edit"),
        Binding("ctrl+b", "branches", "Branches"),
        Binding("ctrl+g", "paste_image", "Image"),
        Binding("ctrl+v", "paste_image", "Image", show=False),
        Binding("ctrl+r", "toggle_thinking", "Think"),
        Binding("ctrl+s", "sessions", "Sessions"),
        Binding("ctrl+t", "templates", "Templates"),
    ]

    current_model: reactive[str] = reactive("")
    current_ctx: reactive[int] = reactive(4096)
    show_thinking: reactive[bool] = reactive(True)

    # --- Lifecycle ---

    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._branches: dict[str, list[dict]] = {"main": []}
        self._active_branch: str = "main"
        self._message_widgets: dict[str, ChatMessage] = {}
        self._streaming = False
        self._cancel_stream = asyncio.Event()
        self._pending_image: str | None = None  # base64 image ready to send
        self.system_prompt = self._cfg.system_prompt
        self.show_thinking = self._cfg.show_thinking
        self.client = AsyncClient()

    @property
    def messages(self) -> list[dict]:
        return self._branches[self._active_branch]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ScrollableContainer(
            Label(
                "Welcome to openbrain. Ask a coding question to get started.\n\n"
                "  Ctrl+M  Change model    Ctrl+L  Clear chat    Ctrl+C  Quit",
                id="welcome",
            ),
            id="chat-container",
        )
        yield Container(
            ContextBar(id="context-bar"),
            Input(placeholder="Ask a coding question...", id="chat-input"),
            Label(id="image-indicator"),
            id="input-wrapper",
        )
        yield Footer()

    def on_mount(self) -> None:
        if self._cfg.default_model:
            self.current_model = self._cfg.default_model
            self.current_ctx = self._cfg.default_ctx
        else:
            try:
                models = Client().list()["models"]
                if models:
                    self.current_model = models[0].model
            except Exception:
                pass
        self._update_subtitle()

        if self._cfg.auto_restore:
            self._restore_latest_session()

        if not self.current_model:
            self.query_one("#chat-input", Input).focus()
        self._update_context_bar()

    # --- Subtitle ---

    def _update_subtitle(self) -> None:
        branch_info = f" [{self._active_branch}]" if len(self._branches) > 1 else ""
        self.sub_title = f"AI coding assistant ({self.current_model}){branch_info}"

    # --- Context Bar ---

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 3)

    def _estimate_usage(self) -> tuple[int, int]:
        total = 0
        for m in self.messages:
            total += self._estimate_tokens(m.get("content", ""))
        if self.system_prompt:
            total += self._estimate_tokens(self.system_prompt)
        return total, self.current_ctx

    def _update_context_bar(self) -> None:
        bar = self.query_one("#context-bar", ContextBar)
        used, total = self._estimate_usage()
        bar.set_usage(used, total, self.current_model)
        bar.set_thinking_visible(self.show_thinking)

    # --- Thinking ---

    @staticmethod
    def _parse_thinking(raw: str) -> tuple[str, str, bool]:
        thinking_parts: list[str] = []
        clean_parts: list[str] = []
        pos = 0
        inside = False
        while pos < len(raw):
            if not inside:
                idx = raw.find("<thinking>", pos)
                if idx == -1:
                    clean_parts.append(raw[pos:])
                    break
                clean_parts.append(raw[pos:idx])
                pos = idx + len("<thinking>")
                inside = True
            else:
                idx = raw.find("</thinking>", pos)
                if idx == -1:
                    thinking_parts.append(raw[pos:])
                    break
                thinking_parts.append(raw[pos:idx])
                pos = idx + len("</thinking>")
                inside = False
        return "".join(thinking_parts).strip(), "".join(clean_parts).strip(), inside

    def action_toggle_thinking(self) -> None:
        self.show_thinking = not self.show_thinking
        self._cfg.show_thinking = self.show_thinking
        save_config_to_disk(self._cfg)
        bar = self.query_one("#context-bar", ContextBar)
        bar.set_thinking_visible(self.show_thinking)
        if self.show_thinking:
            self.notify("Thinking display ON", title="Thinking")
        else:
            self.notify("Thinking display OFF", title="Thinking")
        self._rebuild_chat()

    # --- Image Paste ---

    def action_paste_image(self) -> None:
        data = read_image_from_clipboard()
        if data is None:
            self.notify("No image found in clipboard", severity="warning")
            return
        b64 = base64.b64encode(data).decode()
        self._pending_image = b64
        label = self.query_one("#image-indicator", Label)
        label.update(f" \U0001f5bc\ufe0f  Image ready  ({len(data) // 1024} KB)")
        label.styles.display = "block"
        self.notify("Image pasted from clipboard", title="Image")
        self.query_one("#chat-input", Input).focus()

    def _drop_pending_image(self) -> None:
        self._pending_image = None
        label = self.query_one("#image-indicator", Label)
        label.update("")
        label.styles.display = "none"

    # --- Chat Rebuild ---

    def _rebuild_chat(self) -> None:
        container = self.query_one("#chat-container", ScrollableContainer)
        container.remove_children()
        self.call_later(self._finish_rebuild, container)

    def _finish_rebuild(self, container: ScrollableContainer) -> None:
        self._message_widgets.clear()
        if not self.messages:
            container.mount(
                Label(
                    "Welcome to openbrain. Ask a coding question to get started.\n\n"
                    "  Ctrl+M  Change model    Ctrl+L  Clear chat    Ctrl+C  Quit",
                    id="welcome",
                )
            )
        for msg in self.messages:
            model_name = self.current_model if msg["role"] == "assistant" else ""
            widget = ChatMessage(
                msg["content"], msg["role"], model_name,
                thinking=msg.get("thinking", ""),
                show_thinking=self.show_thinking,
                is_thinking=msg.get("is_thinking", False),
                images=msg.get("images"),
                tool_calls=msg.get("tool_calls_executed"),
            )
            container.mount(widget)
            self._message_widgets[msg["id"]] = widget
        container.scroll_end(animate=False)
        self._update_context_bar()

    # --- Model ---

    def action_change_model(self) -> None:
        self.push_screen(ModelSelectScreen(), callback=self.on_model_select_screen_dismissed)

    def on_model_select_screen_dismissed(self, cfg: ModelConfig) -> None:
        if cfg:
            self.current_model = cfg.model
            self.current_ctx = cfg.num_ctx
            self.notify(f"Switched to {cfg.model} \u00b7 {cfg.num_ctx // 1024}k ctx", title="Model Changed")
            self._update_subtitle()
            self._update_context_bar()

    # --- Action Screen ---

    def action_action_screen(self) -> None:
        self.push_screen(ActionScreen(), callback=self.on_action_screen_dismissed)

    def on_action_screen_dismissed(self, action: str | None) -> None:
        if action == "system_prompt":
            self.push_screen(SystemPromptScreen(), callback=self.on_system_prompt_screen_dismissed)
        elif action == "sessions":
            self.action_sessions()
        elif action == "new_session":
            self.action_new_session()

    def action_new_session(self) -> None:
        if self._cfg.save_history and self.messages:
            self._save_session()
        self._drop_pending_image()
        self._branches = {"main": []}
        self._active_branch = "main"
        self._update_subtitle()
        self._update_context_bar()
        self.query_one("#chat-input", Input).value = ""
        self.query_one("#chat-input", Input).focus()
        self.notify("Started new session", title="Session")
        self._rebuild_chat()

    # --- Sessions ---

    def action_sessions(self) -> None:
        self.push_screen(SessionListScreen(), callback=self.on_session_list_screen_dismissed)

    def on_session_list_screen_dismissed(self, path: str | None) -> None:
        if path:
            self._restore_session(path)

    def _restore_session(self, path: str) -> None:
        try:
            data = json.loads(Path(path).read_text())
        except Exception as e:
            self.notify(f"Failed to load session: {e}", severity="error")
            return
        self.current_model = data.get("model", self.current_model)
        self.current_ctx = data.get("num_ctx", self.current_ctx)
        self.system_prompt = data.get("system_prompt", self.system_prompt)
        if "show_thinking" in data:
            self.show_thinking = data["show_thinking"]
            self._cfg.show_thinking = self.show_thinking
        self._branches = data.get("branches", {"main": []})
        self._active_branch = data.get("active_branch", "main")
        if self._active_branch not in self._branches:
            self._active_branch = "main"
        self._rebuild_chat()
        self._update_subtitle()
        self._update_context_bar()
        self.query_one("#chat-input", Input).focus()
        self.notify("Session loaded", title="Session")

    # --- System Prompt ---

    def action_system_prompt(self) -> None:
        self.push_screen(SystemPromptScreen(), callback=self.on_system_prompt_screen_dismissed)

    def on_system_prompt_screen_dismissed(self, prompt: str) -> None:
        if prompt is not None and prompt != self.system_prompt:
            self.system_prompt = prompt
            self._cfg.system_prompt = prompt
            save_config_to_disk(self._cfg)
            self.notify("System prompt updated", title="System Prompt")
            self._update_context_bar()

    # --- Branches ---

    def action_branches(self) -> None:
        counts = {n: len(msgs) for n, msgs in self._branches.items()}
        self.push_screen(BranchSelectScreen(counts, self._active_branch), callback=self.on_branch_select_screen_dismissed)

    def on_branch_select_screen_dismissed(self, name: str | None) -> None:
        if name and name != self._active_branch:
            self._switch_branch(name)

    def _switch_branch(self, name: str) -> None:
        if name not in self._branches:
            return
        self._active_branch = name
        self._rebuild_chat()
        self._update_subtitle()
        self._update_context_bar()
        self.notify(f"Switched to branch '{name}'", title="Branch")
        self.query_one("#chat-input", Input).focus()

    def action_fork(self, msg_index: int | None = None) -> None:
        if msg_index is None:
            if not self.messages:
                return
            msg_index = len(self.messages) - 1
        name = f"fork-{datetime.now().strftime('%H%M%S')}"
        self._branches[name] = self.messages[: msg_index + 1]
        self._active_branch = name
        self._rebuild_chat()
        self._update_subtitle()
        self._update_context_bar()
        self.notify(f"Created branch '{name}'", title="Fork")

    # --- Templates ---

    def action_templates(self) -> None:
        templates = load_templates()
        if not templates:
            self.notify("No templates found in ~/.config/openbrain/templates/", severity="warning")
            return
        self.push_screen(TemplateSelectScreen(templates), callback=self.on_template_select_screen_dismissed)

    def on_template_select_screen_dismissed(self, name: str | None) -> None:
        if name:
            templates = dict(load_templates())
            prompt = templates.get(name, "")
            if prompt:
                inp = self.query_one("#chat-input", Input)
                inp.value = prompt
                inp.focus()

    # --- Clear ---

    def action_clear(self) -> None:
        self._branches[self._active_branch].clear()
        self._rebuild_chat()
        self._update_context_bar()
        self.query_one("#chat-input", Input).focus()

    # --- Clipboard ---

    def action_copy_last(self) -> None:
        if not self.messages:
            self.notify("No messages to copy", severity="warning")
            return
        last = self.messages[-1]
        if last["role"] != "assistant":
            self.notify("Last message is not from the assistant", severity="warning")
            return
        if copy_to_clipboard(last["content"]):
            self.notify("Copied to clipboard", title="Copy")
        else:
            self.notify("No clipboard tool found (install wl-copy, xclip, or xsel)", severity="error")

    # --- Cancel ---

    def action_cancel_stream(self) -> None:
        if self._streaming:
            self._cancel_stream.set()
            self.notify("Cancelling...", title="Cancel")

    # --- Edit Last Message ---

    def action_edit_last(self) -> None:
        if not self.messages:
            return
        if self._streaming:
            self.action_cancel_stream()
            return
        last_user_idx = None
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i]["role"] == "user":
                last_user_idx = i
                break
        if last_user_idx is None:
            return
        inp = self.query_one("#chat-input", Input)
        inp.value = self.messages[last_user_idx]["content"]
        inp.focus()
        self._editing_idx = last_user_idx

    # --- Input ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        self._editing_idx = None
        if not user_input and not self._pending_image:
            return

        if user_input.startswith("/"):
            self._handle_slash_command(user_input)
            event.input.clear()
            return

        if not self.current_model:
            self.notify("Select a model with Ctrl+M first", title="No model", severity="error")
            return

        event.input.clear()

        editing_idx = getattr(self, "_editing_idx", None)
        if editing_idx is not None:
            msgs = self.messages
            if editing_idx < len(msgs) and msgs[editing_idx]["role"] == "user":
                remove_ids = []
                for idx in range(editing_idx, len(msgs)):
                    remove_ids.append(msgs[idx]["id"])
                msgs[:] = msgs[:editing_idx]
                for rid in remove_ids:
                    w = self._message_widgets.pop(rid, None)
                    if w:
                        w.remove()
            self._editing_idx = None

        images = [self._pending_image] if self._pending_image else []
        self._drop_pending_image()
        msg = make_message("user", user_input, images=images)
        self.messages.append(msg)
        self._add_message_widget(msg)
        self._update_context_bar()
        asyncio.create_task(self._stream_response())

    def _add_message_widget(self, msg: dict) -> None:
        container = self.query_one("#chat-container", ScrollableContainer)
        welcome = container.query_one_optional("#welcome")
        if welcome:
            welcome.remove()
        model_name = self.current_model if msg["role"] == "assistant" else ""
        widget = ChatMessage(
            msg["content"], msg["role"], model_name,
            thinking=msg.get("thinking", ""),
            show_thinking=self.show_thinking,
            is_thinking=msg.get("is_thinking", False),
            images=msg.get("images"),
            tool_calls=msg.get("tool_calls_executed"),
        )
        container.mount(widget)
        self._message_widgets[msg["id"]] = widget
        container.scroll_end(animate=False)

    async def _stream_response(self) -> None:
        self._streaming = True
        self._cancel_stream.clear()

        msg = make_message("assistant", "")
        self.messages.append(msg)
        self._add_message_widget(msg)
        widget = self._message_widgets[msg["id"]]

        ollama_messages = []
        if self.system_prompt:
            ollama_messages.append({"role": "system", "content": self.system_prompt})
        for m in self.messages[:-1]:
            entry: dict = {"role": m["role"], "content": m["content"]}
            if m.get("images"):
                entry["images"] = m["images"]
            ollama_messages.append(entry)

        raw_buffer = ""
        tool_iter = 0
        max_tool_iters = 10

        try:
            while tool_iter < max_tool_iters:
                thinking_blocks: list[str] = []
                content_blocks: list[str] = []
                iter_buffer = ""
                tool_calls = None

                kwargs: dict = {
                    "model": self.current_model,
                    "messages": ollama_messages,
                    "stream": True,
                    "options": {"num_ctx": self.current_ctx},
                }
                if tool_iter == 0 and TOOLS:
                    kwargs["tools"] = TOOLS

                gen = await self.client.chat(**kwargs)
                async for part in gen:
                    if self._cancel_stream.is_set():
                        iter_buffer += "\n\n*[Cancelled]*"
                        break
                    if part.message.tool_calls:
                        tool_calls = part.message.tool_calls
                    t_chunk = getattr(part.message, "thinking", None) or ""
                    c_chunk = getattr(part.message, "content", None) or ""
                    if t_chunk:
                        thinking_blocks.append(t_chunk)
                    if c_chunk:
                        content_blocks.append(c_chunk)
                        iter_buffer += c_chunk
                    if t_chunk or c_chunk:
                        thinking = "".join(thinking_blocks).strip()
                        if not thinking:
                            if iter_buffer.strip():
                                thinking, clean, is_thinking = self._parse_thinking(iter_buffer)
                            else:
                                clean = ""
                                is_thinking = False
                        else:
                            clean = "".join(content_blocks).strip()
                            is_thinking = not bool(clean)
                        msg["thinking"] = thinking
                        msg["content"] = clean
                        msg["is_thinking"] = is_thinking
                        widget.update_content(
                            content=clean, thinking=thinking,
                            show_thinking=self.show_thinking,
                            is_thinking=is_thinking,
                        )
                        if len(raw_buffer + iter_buffer) % 20 == 0:
                            container = self.query_one("#chat-container", ScrollableContainer)
                            container.scroll_end(animate=False)
                            self._update_context_bar()

                if not tool_calls:
                    raw_buffer += iter_buffer
                    break

                assistant_msg = {
                    "role": "assistant",
                    "content": "".join(content_blocks).strip(),
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                                if isinstance(tc.function.arguments, dict)
                                else {},
                            }
                        }
                        for tc in tool_calls
                    ],
                }
                ollama_messages.append(assistant_msg)

                for tc in tool_calls:
                    fn = tc.function.name
                    args = (
                        tc.function.arguments
                        if isinstance(tc.function.arguments, dict)
                        else {}
                    )
                    widget.add_tool_call(fn, args)
                    handler = TOOL_DISPATCH.get(fn)
                    result = (
                        await handler(**args)
                        if handler
                        else f"Unknown tool: {fn}"
                    )
                    widget.set_tool_done(fn)
                    ollama_messages.append({
                        "role": "tool",
                        "content": result,
                        "name": fn,
                    })

                msg["tool_calls_executed"] = [
                    {"name": tc["name"], "args": tc["args"]}
                    for tc in widget._tool_calls
                ]
                raw_buffer += iter_buffer
                tool_iter += 1
        except Exception as e:
            content_blocks = [raw_buffer] if raw_buffer else []
            content_blocks.append(f"\n\n**Error:** {e}")
            re_buffer = raw_buffer + f"\n\n**Error:** {e}"
            re_thinking, re_clean, _ = self._parse_thinking(re_buffer)
            msg["thinking"] = re_thinking
            msg["content"] = re_clean
            widget.update_content(content=re_clean, thinking=re_thinking)

        msg["raw"] = raw_buffer
        container = self.query_one("#chat-container", ScrollableContainer)
        container.scroll_end(animate=False)
        self._update_context_bar()
        self._streaming = False

        if self._cfg.save_history:
            self._save_session()

    # --- Slash Commands ---

    def _handle_slash_command(self, cmd: str) -> None:
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command in ("/clear", "/cls"):
            self.action_clear()
        elif command == "/model":
            self.action_change_model()
        elif command == "/ctx":
            if arg:
                try:
                    self.current_ctx = int(arg)
                    self._update_context_bar()
                    self.notify(f"Context window set to {int(arg):,}", title="Context")
                except ValueError:
                    self.notify("Usage: /ctx <number>", severity="warning")
            else:
                self.notify(f"Current context: {self.current_ctx:,}", title="Context")
        elif command == "/system":
            self.action_system_prompt()
        elif command == "/export":
            self._save_session()
            self.notify("Session saved", title="Export")
        elif command == "/help":
            self._show_help()
        elif command == "/fork":
            self.action_fork()
        elif command == "/branches":
            self.action_branches()
        elif command in ("/image", "/img"):
            if arg:
                b64 = image_path_to_base64(arg)
                if b64:
                    self._pending_image = b64
                    path = Path(arg)
                    label = self.query_one("#image-indicator", Label)
                    label.update(f" \U0001f5bc\ufe0f  {path.name}  ({path.stat().st_size // 1024} KB)")
                    label.styles.display = "block"
                    self.notify(f"Loaded image: {path.name}", title="Image")
                else:
                    self.notify(f"Could not load image: {arg}", severity="error")
            else:
                self.action_paste_image()
        elif command == "/thinking":
            self.action_toggle_thinking()
        elif command == "/sessions":
            self.action_sessions()
        elif command == "/template":
            self.action_templates()
        elif command == "/copy":
            self.action_copy_last()
        elif command == "/edit":
            self.action_edit_last()
        elif command == "/cancel":
            self.action_cancel_stream()
        else:
            self.notify(f"Unknown command: {command}", severity="warning")

    def _show_help(self) -> None:
        help_text = (
            "[bold #89b4fa]Openbrain Commands[/]\n\n"
            "[bold]Slash commands:[/]\n"
            "  /clear, /cls    Clear chat\n"
            "  /model           Change model\n"
            "  /ctx <n>         Set context window\n"
            "  /system          Edit system prompt\n"
            "  /fork            Fork conversation at last message\n"
            "  /branches        Switch branches\n"
            "  /template        Load a prompt template\n"
            "  /image, /img     Paste image (clipboard or path)\n"
            "  /thinking        Toggle thinking display\n"
            "  /sessions        Browse & load previous sessions\n"
            "  /export          Save session\n"
            "  /copy            Copy last assistant response\n"
            "  /edit            Edit last user message\n"
            "  /cancel          Cancel streaming\n"
            "  /help            Show this help\n\n"
            "[bold]Keyboard shortcuts:[/]\n"
            "  Ctrl+M   Change model\n"
            "  Ctrl+L   Clear chat\n"
            "  Ctrl+P   System prompt\n"
            "  Ctrl+G   Paste image\n"
            "  Ctrl+R   Toggle thinking\n"
            "  Ctrl+K   Cancel streaming\n"
            "  Ctrl+Y   Copy last response\n"
            "  Ctrl+Up  Edit last message\n"
            "  Ctrl+S   Sessions\n"
            "  Ctrl+B   Switch branches\n"
            "  Ctrl+T   Load template\n"
            "  Ctrl+C   Quit"
        )
        self.notify(help_text, title="Help", timeout=15)

    # --- Persistence ---

    def _session_path(self) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    def _save_session(self) -> None:
        path = self._session_path()
        data = {
            "model": self.current_model,
            "num_ctx": self.current_ctx,
            "system_prompt": self.system_prompt,
            "active_branch": self._active_branch,
            "branches": self._branches,
            "show_thinking": self.show_thinking,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            path.write_text(json.dumps(data, indent=2))
            old = sorted(DATA_DIR.glob("session-*.json"), reverse=True)
            for f in old[20:]:
                f.unlink(missing_ok=True)
        except Exception as e:
            self.notify(f"Failed to save session: {e}", severity="error")

    def _restore_latest_session(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        sessions = sorted(DATA_DIR.glob("session-*.json"), reverse=True)
        if not sessions:
            return
        try:
            data = json.loads(sessions[0].read_text())
            self.current_model = data.get("model", self.current_model)
            self.current_ctx = data.get("num_ctx", self.current_ctx)
            self.system_prompt = data.get("system_prompt", self.system_prompt)
            if "show_thinking" in data:
                self.show_thinking = data["show_thinking"]
                self._cfg.show_thinking = self.show_thinking
            self._branches = data.get("branches", {"main": []})
            self._active_branch = data.get("active_branch", "main")
            if self._active_branch not in self._branches:
                self._active_branch = "main"
            self._rebuild_chat()
            self._update_subtitle()
            self._update_context_bar()
        except Exception as e:
            self.notify(f"Failed to restore session: {e}", severity="warning")
