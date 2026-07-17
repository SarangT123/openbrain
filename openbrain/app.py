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
from textual.widgets import Footer, Header, Input, Label, TextArea

from openbrain.agent import run_agent_turn
from openbrain.config import DATA_DIR, DEFAULT_SYSTEM_PROMPT, load_config, save_config_to_disk
from openbrain.tools import TOOLS
from openbrain.screens.action import ActionScreen
from openbrain.screens.agent_settings import AgentSettingsScreen
from openbrain.screens.benchmark import BenchmarkScreen
from openbrain.screens.branch_select import BranchSelectScreen
from openbrain.screens.model_select import ModelSelectScreen
from openbrain.screens.session_list import SessionListScreen
from openbrain.screens.rename_session import RenameSessionScreen
from openbrain.screens.system_prompt import SystemPromptScreen
from openbrain.screens.prompt_preset import PromptPresetScreen
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
        max-height: 13;
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
        margin: 0;
        height: auto;
        min-height: 3;
        max-height: 12;
    }
    #chat-input:focus {
        border: none;
    }
    #chat-input > TextAreaCursor {
        color: #f5c2e7;
    }
    #chat-input > TextAreaSelection {
        background: #585b70;
    }
    #chat-input .textual-textarea-scrollbar {
        scrollbar-color: #45475a;
        scrollbar-color-hover: #585b70;
        scrollbar-color-active: #89b4fa;
    }
    #image-indicator {
        height: 1;
        background: #313244;
        color: #f9e2af;
        padding: 0 2;
        display: none;
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
    SessionListScreen,
    AgentSettingsScreen,
    BenchmarkScreen {
        background: #11111b;
    }
    ActionScreen > Container,
    ModelSelectScreen > Container,
    SystemPromptScreen > Container,
    BranchSelectScreen > Container,
    TemplateSelectScreen > Container,
    RenameSessionScreen > Container,
    SessionListScreen > Container,
    AgentSettingsScreen > Container,
    BenchmarkScreen > Container {
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
    RenameSessionScreen .title,
    SessionListScreen .title,
    AgentSettingsScreen .title,
    BenchmarkScreen .title {
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
    SessionListScreen .hint,
    RenameSessionScreen .hint,
    AgentSettingsScreen .hint,
    BenchmarkScreen .hint {
        color: #6c7086;
        padding-top: 0;
    }
    RenameSessionScreen Input {
        background: #313244;
        color: #cdd6f4;
        border: none;
        margin-bottom: 0;
    }
    RenameSessionScreen Input:focus {
        border: none;
    }
    AgentSettingsScreen Input,
    BenchmarkScreen Input {
        background: #313244;
        color: #cdd6f4;
        border: none;
        margin-bottom: 0;
        width: 20;
    }
    AgentSettingsScreen Input:focus,
    BenchmarkScreen Input:focus {
        border: none;
    }
    AgentSettingsScreen Horizontal,
    BenchmarkScreen Horizontal {
        height: 3;
        align: left middle;
        margin-bottom: 0;
    }
    AgentSettingsScreen Horizontal > Label,
    BenchmarkScreen Horizontal > Label {
        width: 30;
        color: #a6adc8;
    }
    AgentSettingsScreen Switch,
    BenchmarkScreen Switch {
        margin-left: 30;
    }
    BenchmarkScreen Button {
        margin-right: 1;
    }
    BenchmarkScreen #bench-log {
        background: #11111b;
        color: #cdd6f4;
        border: solid #45475a;
        height: 10;
        margin-top: 1;
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
        Binding("ctrl+left", "predict_down", "Pred-", show=False),
        Binding("ctrl+right", "predict_up", "Pred+", show=False),
        Binding("ctrl+enter", "submit_input", "Send", show=False),
        Binding("ctrl+e", "cycle_prompt_preset", "Prompt"),
        Binding("ctrl+shift+e", "prompt_presets", "Presets"),
    ]

    current_model: reactive[str] = reactive("")
    current_ctx: reactive[int] = reactive(4096)
    current_predict: reactive[int] = reactive(8192)
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
        self.system_prompt = self._cfg.system_prompt or DEFAULT_SYSTEM_PROMPT
        self.show_thinking = self._cfg.show_thinking
        self.current_predict = self._cfg.default_predict
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
            TextArea(placeholder="Ask a coding question... (Ctrl+Enter to send)", id="chat-input", compact=True, highlight_cursor_line=False),
            Label(id="image-indicator"),
            id="input-wrapper",
        )
        yield Footer()

    def on_mount(self) -> None:
        if self._cfg.auto_restore:
            self._restore_latest_session()
        if self._cfg.default_model:
            self.current_model = self._cfg.default_model
            self.current_ctx = self._cfg.default_ctx
            self.current_predict = self._cfg.default_predict
        else:
            try:
                models = Client().list()["models"]
                if models:
                    self.current_model = models[0].model
            except Exception:
                pass
        self._update_subtitle()

        if not self.current_model:
            self.query_one("#chat-input", TextArea).focus()
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
        bar.set_predict(self.current_predict)

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

    # --- Predict ---

    PREDICT_PRESETS = [0, 512, 1024, 2048, 4096, 8192, 16384]

    def action_predict_down(self) -> None:
        presets = self.PREDICT_PRESETS
        cur = self.current_predict
        i = presets.index(cur) if cur in presets else max(i for i, v in enumerate(presets) if v < cur)
        if i > 0:
            self.current_predict = presets[i - 1]
        elif cur > 0:
            self.current_predict = 0
        self._update_context_bar()
        lbl = f"{self.current_predict:,}" if self.current_predict > 0 else "\u221e"
        self.notify(f"Max tokens set to {lbl}", title="Predict")

    def action_predict_up(self) -> None:
        presets = self.PREDICT_PRESETS
        cur = self.current_predict
        i = presets.index(cur) if cur in presets else max(i for i, v in enumerate(presets) if v <= cur)
        if i < len(presets) - 1:
            self.current_predict = presets[i + 1]
        elif cur >= presets[-1]:
            self.current_predict = 0
        self._update_context_bar()
        lbl = f"{self.current_predict:,}" if self.current_predict > 0 else "\u221e"
        self.notify(f"Max tokens set to {lbl}", title="Predict")

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
        self.query_one("#chat-input", TextArea).focus()

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
        elif action == "agent_settings":
            self.push_screen(AgentSettingsScreen(), callback=self.on_agent_settings_dismissed)
        elif action == "benchmark":
            self.push_screen(BenchmarkScreen(), callback=self.on_benchmark_screen_dismissed)
        elif action == "prompt_presets":
            self.action_prompt_presets()

    def action_new_session(self) -> None:
        if self._cfg.save_history and self.messages:
            self._save_session()
        self._drop_pending_image()
        self._branches = {"main": []}
        self._active_branch = "main"
        self._update_subtitle()
        self._update_context_bar()
        self.query_one("#chat-input", TextArea).text = ""
        self.query_one("#chat-input", TextArea).focus()
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
        self.current_predict = data.get("num_predict", self.current_predict)
        self.system_prompt = data.get("system_prompt", self.system_prompt) or DEFAULT_SYSTEM_PROMPT
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
        self.query_one("#chat-input", TextArea).focus()
        self.notify("Session loaded", title="Session")

    # --- System Prompt ---

    def action_system_prompt(self) -> None:
        self.push_screen(SystemPromptScreen(), callback=self.on_system_prompt_screen_dismissed)

    def on_system_prompt_screen_dismissed(self, prompt: str) -> None:
        if prompt is not None and prompt != self.system_prompt:
            self.system_prompt = prompt or DEFAULT_SYSTEM_PROMPT
            self._cfg.system_prompt = prompt
            save_config_to_disk(self._cfg)
            self.notify("System prompt updated", title="System Prompt")
            self._update_context_bar()

    def _apply_preset(self, name: str, prompt: str) -> None:
        self.system_prompt = prompt
        self._cfg.system_prompt = prompt
        self._cfg.active_preset = name
        save_config_to_disk(self._cfg)
        self._update_context_bar()
        self.notify(f"System prompt: {name}", title="Prompt Preset")

    def action_cycle_prompt_preset(self) -> None:
        from openbrain.config import SYSTEM_PROMPT_PRESETS

        names = [n for n, _ in SYSTEM_PROMPT_PRESETS]
        try:
            current_idx = names.index(self._cfg.active_preset)
        except ValueError:
            current_idx = -1
        next_idx = (current_idx + 1) % len(SYSTEM_PROMPT_PRESETS)
        name, prompt = SYSTEM_PROMPT_PRESETS[next_idx]
        self._apply_preset(name, prompt)

    def action_prompt_presets(self) -> None:
        self.push_screen(PromptPresetScreen(), callback=self._on_preset_picker)

    def _on_preset_picker(self, name: str | None) -> None:
        if name is None:
            return
        from openbrain.config import preset_by_name
        prompt = preset_by_name(name)
        if prompt is not None:
            self._apply_preset(name, prompt)

    def on_agent_settings_dismissed(self, data: dict | None) -> None:
        if data is not None:
            for key, value in data.items():
                setattr(self._cfg, key, value)
            save_config_to_disk(self._cfg)
            self.notify("Agent settings saved", title="Settings")

    def on_benchmark_screen_dismissed(self, _: None) -> None:
        pass

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
        self.query_one("#chat-input", TextArea).focus()

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
                inp = self.query_one("#chat-input", TextArea)
                inp.text = prompt
                inp.focus()

    # --- Clear ---

    def action_clear(self) -> None:
        self._branches[self._active_branch].clear()
        self._rebuild_chat()
        self._update_context_bar()
        self.query_one("#chat-input", TextArea).focus()

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
        inp = self.query_one("#chat-input", TextArea)
        inp.text = self.messages[last_user_idx]["content"]
        inp.focus()
        self._editing_idx = last_user_idx

    # --- Input ---

    def action_submit_input(self) -> None:
        inp = self.query_one("#chat-input", TextArea)
        user_input = inp.text.strip()
        self._editing_idx = None
        if not user_input and not self._pending_image:
            return

        if user_input.startswith("/"):
            self._handle_slash_command(user_input)
            inp.text = ""
            return

        if not self.current_model:
            self.notify("Select a model with Ctrl+M first", title="No model", severity="error")
            return

        inp.text = ""

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

        content_buffer = ""
        thinking_buffer = ""

        def _on_chunk(content: str, thinking: str) -> None:
            nonlocal content_buffer, thinking_buffer
            content_buffer = content
            thinking_buffer = thinking
            if thinking:
                clean = content
                is_thinking = not bool(clean)
                widget.update_content(
                    content=clean, thinking=thinking,
                    show_thinking=self.show_thinking,
                    is_thinking=is_thinking,
                )
            else:
                t, clean, is_thinking = self._parse_thinking(content)
                widget.update_content(
                    content=clean, thinking=t,
                    show_thinking=self.show_thinking,
                    is_thinking=is_thinking,
                )
            container = self.query_one("#chat-container", ScrollableContainer)
            container.scroll_end(animate=False)
            self._update_context_bar()

        def _on_tool_call(tc: dict) -> None:
            widget.add_tool_call(tc.get("name", ""), tc.get("args", {}))

        def _on_tool_result(fn: str, _result: str) -> None:
            widget.set_tool_done(fn)

        try:
            result = await run_agent_turn(
                self.client, self.current_model, ollama_messages, TOOLS,
                temperature=self._cfg.temperature,
                seed=self._cfg.seed,
                num_ctx=self.current_ctx,
                num_predict=self.current_predict,
                keep_alive=self._cfg.keep_alive,
                force_tool_use=self._cfg.force_tool_use,
                force_tool_retry_limit=self._cfg.force_tool_retry_limit,
                calc_guard_enabled=self._cfg.calc_guard_enabled,
                calc_guard_threshold=self._cfg.calc_guard_threshold,
                on_chunk=_on_chunk,
                on_tool_call=_on_tool_call,
                on_tool_result=_on_tool_result,
                cancel_event=self._cancel_stream,
            )

            for tc in result.tool_calls:
                widget.set_tool_done(tc["name"])

            final_text = result.final_text.replace("<channel|>", "")
            content_buffer = content_buffer.replace("<channel|>", "")
            msg["content"] = final_text
            msg["raw"] = content_buffer
            msg["tool_calls_executed"] = result.tool_calls
            if thinking_buffer:
                msg["thinking"] = thinking_buffer
            else:
                t, clean, _ = self._parse_thinking(final_text)
                if t:
                    msg["thinking"] = t
                    msg["content"] = clean

        except Exception as e:
            err_msg = str(e)
            if "out of memory" in err_msg.lower() or "oom" in err_msg.lower():
                err_msg = (
                    f"**Out of VRAM:** {err_msg}\n\n"
                    f"The model `{self.current_model}` does not fit in available GPU memory. "
                    "Try a smaller model, set keep_alive='0' to unload other models, "
                    "or free system memory."
                )
            content_buffer += f"\n\n**Error:** {err_msg}"
            re_thinking, re_clean, _ = self._parse_thinking(content_buffer)
            msg["thinking"] = re_thinking
            msg["content"] = re_clean
            widget.update_content(content=re_clean, thinking=re_thinking)

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
        elif command == "/predict":
            if arg:
                try:
                    self.current_predict = int(arg)
                    self._update_context_bar()
                    lbl = f"{int(arg):,}" if int(arg) > 0 else "\u221e"
                    self.notify(f"Max tokens set to {lbl}", title="Predict")
                except ValueError:
                    self.notify("Usage: /predict <number> (0 = unlimited)", severity="warning")
            else:
                lbl = f"{self.current_predict:,}" if self.current_predict > 0 else "\u221e"
                self.notify(f"Current predict: {lbl}", title="Predict")
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
            "  /predict <n>     Set max tokens (0 = unlimited)\n"
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
            "  Ctrl+E   Cycle prompt preset\n"
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

    @staticmethod
    def _generate_session_name(branches: dict[str, list[dict]], active_branch: str) -> str:
        msgs = branches.get(active_branch, [])
        for m in msgs:
            if m.get("role") == "user":
                text = m["content"].strip()
                name = text[:55].replace("\n", " ").strip()
                if len(text) > 55:
                    name += "..."
                return name if name else "Untitled"
        return "Untitled"

    def _session_path(self) -> Path:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    def _save_session(self) -> None:
        path = self._session_path()
        data = {
            "name": self._generate_session_name(self._branches, self._active_branch),
            "model": self.current_model,
            "num_ctx": self.current_ctx,
            "num_predict": self.current_predict,
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
            self.current_predict = data.get("num_predict", self.current_predict)
            self.system_prompt = data.get("system_prompt", self.system_prompt) or DEFAULT_SYSTEM_PROMPT
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
