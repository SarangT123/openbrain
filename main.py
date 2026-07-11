import asyncio
import json
import re
import subprocess
import tomllib
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from ollama import AsyncClient, Client
from pylatexenc.latex2text import LatexNodes2Text
from rich.console import Group
from rich.markdown import Markdown
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TextArea,
)


CONFIG_DIR = Path.home() / ".config" / "openbrain"
CONFIG_PATH = CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "openbrain" / "sessions"
TEMPLATE_DIR = CONFIG_DIR / "templates"


@dataclass
class Config:
    default_model: str = ""
    default_ctx: int = 4096
    system_prompt: str = ""
    save_history: bool = True
    auto_restore: bool = True


def load_config() -> Config:
    cfg = Config()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "rb") as f:
                data = tomllib.load(f)
            cfg.default_model = data.get("model", "")
            cfg.default_ctx = data.get("num_ctx", 4096)
            cfg.system_prompt = data.get("system_prompt", "")
            cfg.save_history = data.get("save_history", True)
            cfg.auto_restore = data.get("auto_restore", True)
        except Exception:
            pass
    else:
        save_config_to_disk(cfg)
    return cfg


def save_config_to_disk(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f'model = "{cfg.default_model}"',
        f"num_ctx = {cfg.default_ctx}",
    ]
    if cfg.system_prompt:
        esc = cfg.system_prompt.replace('"', '\\"')
        lines.append(f'system_prompt = "{esc}"')
    else:
        lines.append('system_prompt = ""')
    lines.append(f"save_history = {'true' if cfg.save_history else 'false'}")
    lines.append(f"auto_restore = {'true' if cfg.auto_restore else 'false'}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n")


def copy_to_clipboard(text: str) -> bool:
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-i", "-b"]):
        try:
            subprocess.run(cmd, input=text, text=True, timeout=2, capture_output=True)
            return True
        except FileNotFoundError:
            pass
    return False


CONTEXT_PRESETS = [2048, 4096, 8192, 16384, 32768, 65536, 131072]


@dataclass
class ModelConfig:
    model: str
    num_ctx: int = 4096


def make_message(role: str, content: str, **kw) -> dict:
    msg = {"id": uuid.uuid4().hex[:12], "role": role, "content": content}
    msg.update(kw)
    return msg


_LATEX_CONVERTER = LatexNodes2Text()


def _latex_to_text(match: re.Match) -> str:
    raw = match.group(1)
    try:
        converted = _LATEX_CONVERTER.latex_to_text(raw)
    except Exception:
        converted = raw
    return f"`{converted}`"


def preprocess_math(text: str) -> str:
    text = re.sub(r"\$\$(.+?)\$\$", _latex_to_text, text, flags=re.DOTALL)
    text = re.sub(r"\$(.+?)\$", _latex_to_text, text)
    return text


class ModelSelectScreen(ModalScreen[ModelConfig]):
    def __init__(self):
        super().__init__()
        self.models: list[str] = []

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Select model", classes="title"),
            ListView(id="model-list"),
            Label("Type a custom model name:", classes="hint"),
            Input(placeholder="e.g. llama3.2:latest", id="custom-model"),
            Label("Context window", classes="title"),
            ListView(id="ctx-list"),
            Label("Custom context size:", classes="hint"),
            Input(placeholder="e.g. 4096", id="custom-ctx"),
            classes="model-dialog",
        )

    def on_mount(self) -> None:
        self._selected_model = ""
        self._selected_ctx = 4096
        self._fetch_models()
        self._populate_ctx()

    def _fetch_models(self) -> None:
        try:
            self.models = sorted(m.model for m in Client().list()["models"])
        except Exception:
            self.models = []
        list_view = self.query_one("#model-list", ListView)
        for m in self.models:
            item = ListItem(Label(m))
            item.model_name = m
            list_view.append(item)

    def _populate_ctx(self) -> None:
        ctx_list = self.query_one("#ctx-list", ListView)
        for n in CONTEXT_PRESETS:
            item = ListItem(Label(f"{n // 1024}k"))
            item.ctx_value = n
            ctx_list.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None:
            return
        if event.list_view.id == "model-list":
            self._selected_model = event.item.model_name
        elif event.list_view.id == "ctx-list":
            self._selected_ctx = event.item.ctx_value
        self._try_dismiss()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "custom-model":
            self._selected_model = event.value.strip()
        elif event.input.id == "custom-ctx":
            try:
                self._selected_ctx = int(event.value.strip())
            except ValueError:
                return
        self._try_dismiss()

    def _try_dismiss(self) -> None:
        if self._selected_model and self._selected_ctx:
            self.dismiss(ModelConfig(self._selected_model, self._selected_ctx))


class SystemPromptScreen(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("System prompt (sent as context to the model)", classes="title"),
            TextArea(id="sys-prompt-editor", show_line_numbers=True),
            Label("Press Ctrl+S to save, Escape to cancel", classes="hint"),
            classes="sysprompt-dialog",
        )

    def on_mount(self) -> None:
        app = self.app
        if hasattr(app, "system_prompt") and app.system_prompt:
            self.query_one("#sys-prompt-editor", TextArea).text = app.system_prompt
        self.query_one("#sys-prompt-editor", TextArea).focus()

    def on_text_area_changed(self, _) -> None:
        pass

    def key_escape(self) -> None:
        app = self.app
        self.dismiss(app.system_prompt if hasattr(app, "system_prompt") else "")

    def key_ctrl_s(self) -> None:
        self.dismiss(self.query_one("#sys-prompt-editor", TextArea).text)


class BranchSelectScreen(ModalScreen[str | None]):
    def __init__(self, branches: dict[str, int], active: str):
        super().__init__()
        self.branches = branches
        self.active = active

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Branches", classes="title"),
            ListView(id="branch-list"),
            Label("Select a branch to switch to", classes="hint"),
            classes="branch-dialog",
        )

    def on_mount(self) -> None:
        lv = self.query_one("#branch-list", ListView)
        for name, count in self.branches.items():
            indicator = " \u25b6" if name == self.active else ""
            item = ListItem(Label(f"{name}{indicator}  ({count} msgs)"))
            item.branch_name = name
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item:
            self.dismiss(event.item.branch_name)


class TemplateSelectScreen(ModalScreen[str | None]):
    def __init__(self, templates: list[tuple[str, str]]):
        super().__init__()
        self.templates = templates

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Prompt templates", classes="title"),
            ListView(id="template-list"),
            Label("Select a template to load into input", classes="hint"),
            classes="template-dialog",
        )

    def on_mount(self) -> None:
        lv = self.query_one("#template-list", ListView)
        for name, preview in self.templates:
            label = f"{name}  \u2014  {preview[:60]}{'...' if len(preview) > 60 else ''}"
            item = ListItem(Label(label))
            item.tpl_name = name
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item:
            self.dismiss(event.item.tpl_name)


class ActionScreen(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Actions", classes="title"),
            ListView(id="action-list"),
            Label("Select an action", classes="hint"),
            classes="action-dialog",
        )

    def on_mount(self) -> None:
        lv = self.query_one("#action-list", ListView)
        for action, label in [
            ("system_prompt", "Edit System Prompt"),
            ("new_session", "New Session"),
        ]:
            item = ListItem(Label(label))
            item.action_name = action
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item:
            self.dismiss(event.item.action_name)


class ChatMessage(Static):
    def __init__(self, content: str, role: str, model: str = "") -> None:
        self.role = role
        self.model = model
        super().__init__(content)

    def render(self) -> Text | Group:
        text = str(self.content)
        if self.role == "user":
            return Text.assemble(
                Text(" \u2502 ", style="#585b70"),
                Text("you", style="bold #89b4fa"),
                Text(f" {text}", style="#cdd6f4"),
            )
        label = self.model or "assistant"
        display = preprocess_math(text) if text else ""
        return Group(
            Text.assemble(
                Text(" \u2502 ", style="#585b70"),
                Text(label, style="bold #a6e3a1"),
            ),
            Markdown(display, code_theme="catppuccin-frappe"),
        )


class ContextBar(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.used = 0
        self.total = 4096
        self.model = ""

    def set_usage(self, used: int, total: int, model: str = "") -> None:
        self.used = used
        self.total = total
        self.model = model
        self.refresh()

    def render(self) -> Text:
        if self.total == 0:
            return Text("")
        ratio = self.used / self.total
        bar_width = 20
        filled = min(int(ratio * bar_width), bar_width)
        empty = bar_width - filled

        blocks = "\u2583" * filled + "\u2591" * empty
        pct = ratio * 100

        if pct > 90:
            color = "#f38ba8"
        elif pct > 70:
            color = "#fab387"
        else:
            color = "#a6e3a1"

        used_label = f"{self.used:,}" if self.used >= 0 else "?"
        total_label = f"{self.total:,}"
        model_label = self.model.split(":")[0] if self.model else ""

        parts = [Text(" ")]
        if model_label:
            parts.append(Text(f"\u2502 {model_label} ", style="#585b70"))
        parts.append(Text(blocks, style=color))
        parts.append(Text(f" {pct:.0f}%", style="#6c7086"))
        parts.append(Text(f"  {used_label}/{total_label} ctx", style="#585b70"))
        return Text.assemble(*parts)


def _load_templates() -> list[tuple[str, str]]:
    if not TEMPLATE_DIR.is_dir():
        return []
    result = []
    for f in sorted(TEMPLATE_DIR.iterdir()):
        if f.suffix in (".txt", ".toml", ".md"):
            try:
                content = f.read_text().strip()
                name = f.stem.replace("_", " ").replace("-", " ").title()
                if f.suffix == ".toml":
                    try:
                        data = tomllib.loads(content)
                        name = data.get("name", name)
                        content = data.get("prompt", content)
                    except Exception:
                        pass
                result.append((name, content))
            except Exception:
                pass
    return result


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
        height: 4;
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
    #chat-input .textual-input-cursor {
        color: #f5c2e7;
    }
    ChatMessage {
        margin: 0 0 0 0;
        padding: 0 1;
        background: #1e1e2e;
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
    TemplateSelectScreen {
        background: #11111b;
    }
    ActionScreen > Container,
    ModelSelectScreen > Container,
    SystemPromptScreen > Container,
    BranchSelectScreen > Container,
    TemplateSelectScreen > Container {
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
    ActionScreen .title {
        text-style: bold;
        color: #b4befe;
        padding-top: 1;
        padding-bottom: 0;
    }
    ModelSelectScreen .hint,
    SystemPromptScreen .hint,
    BranchSelectScreen .hint,
    TemplateSelectScreen .hint,
    ActionScreen .hint {
        color: #6c7086;
        padding-top: 0;
    }
    ModelSelectScreen ListView,
    BranchSelectScreen ListView,
    TemplateSelectScreen ListView,
    ActionScreen ListView {
        height: 8;
        border: none;
        background: #313244;
    }
    ModelSelectScreen ListView#ctx-list {
        height: 5;
    }
    ModelSelectScreen ListItem,
    BranchSelectScreen ListItem,
    TemplateSelectScreen ListItem,
    ActionScreen ListItem {
        background: #313244;
        color: #cdd6f4;
        padding: 0 1;
    }
    ModelSelectScreen ListItem:hover,
    BranchSelectScreen ListItem:hover,
    TemplateSelectScreen ListItem:hover,
    ActionScreen ListItem:hover {
        background: #45475a;
    }
    ModelSelectScreen ListView:focus > ListItem:hover,
    BranchSelectScreen ListView:focus > ListItem:hover,
    TemplateSelectScreen ListView:focus > ListItem:hover,
    ActionScreen ListView:focus > ListItem:hover {
        background: #585b70;
    }
    ModelSelectScreen ListView > ListItem:focus,
    BranchSelectScreen ListView > ListItem:focus,
    TemplateSelectScreen ListView > ListItem:focus,
    ActionScreen ListView > ListItem:focus {
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
        Binding("ctrl+t", "templates", "Templates"),
    ]

    current_model: reactive[str] = reactive("")
    current_ctx: reactive[int] = reactive(4096)

    @property
    def messages(self) -> list[dict]:
        return self._branches[self._active_branch]

    def __init__(self):
        super().__init__()
        self._cfg = load_config()
        self._branches: dict[str, list[dict]] = {"main": []}
        self._active_branch: str = "main"
        self._message_widgets: dict[str, ChatMessage] = {}
        self._streaming = False
        self._cancel_stream = asyncio.Event()
        self.system_prompt = self._cfg.system_prompt
        self.client = AsyncClient()

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

    def _update_subtitle(self) -> None:
        branch_info = f" [{self._active_branch}]" if len(self._branches) > 1 else ""
        self.sub_title = f"AI coding assistant ({self.current_model}){branch_info}"

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
            widget = ChatMessage(msg["content"], msg["role"], model_name)
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
        elif action == "new_session":
            self.action_new_session()

    def action_new_session(self) -> None:
        if self._cfg.save_history and self.messages:
            self._save_session()
        self._branches = {"main": []}
        self._active_branch = "main"
        self._update_subtitle()
        self._update_context_bar()
        self.query_one("#chat-input", Input).value = ""
        self.query_one("#chat-input", Input).focus()
        self.notify("Started new session", title="Session")
        self._rebuild_chat()

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
        templates = _load_templates()
        if not templates:
            self.notify("No templates found in ~/.config/openbrain/templates/", severity="warning")
            return
        self.push_screen(TemplateSelectScreen(templates), callback=self.on_template_select_screen_dismissed)

    def on_template_select_screen_dismissed(self, name: str | None) -> None:
        if name:
            templates = dict(_load_templates())
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
        if not user_input:
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

        msg = make_message("user", user_input)
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
        widget = ChatMessage(msg["content"], msg["role"], model_name)
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
            ollama_messages.append({"role": m["role"], "content": m["content"]})

        buffer = ""
        try:
            gen = await self.client.chat(
                model=self.current_model,
                messages=ollama_messages,
                stream=True,
                options={"num_ctx": self.current_ctx},
            )
            async for part in gen:
                if self._cancel_stream.is_set():
                    buffer += "\n\n*[Cancelled]*"
                    break
                if chunk := part.message.content:
                    buffer += chunk
                    widget.update(buffer)
                    msg["content"] = buffer
                    if len(buffer) % 20 == 0:
                        container = self.query_one("#chat-container", ScrollableContainer)
                        container.scroll_end(animate=False)
                        self._update_context_bar()
        except Exception as e:
            buffer += f"\n\n**Error:** {e}"
            widget.update(buffer)
            msg["content"] = buffer

        msg["content"] = buffer
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
            "  /export          Save session\n"
            "  /copy            Copy last assistant response\n"
            "  /edit            Edit last user message\n"
            "  /cancel          Cancel streaming\n"
            "  /help            Show this help\n\n"
            "[bold]Keyboard shortcuts:[/]\n"
            "  Ctrl+M   Change model\n"
            "  Ctrl+L   Clear chat\n"
            "  Ctrl+P   System prompt\n"
            "  Ctrl+K   Cancel streaming\n"
            "  Ctrl+Y   Copy last response\n"
            "  Ctrl+Up  Edit last message\n"
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
            self._branches = data.get("branches", {"main": []})
            self._active_branch = data.get("active_branch", "main")
            if self._active_branch not in self._branches:
                self._active_branch = "main"
            self._rebuild_chat()
            self._update_subtitle()
            self._update_context_bar()
        except Exception as e:
            self.notify(f"Failed to restore session: {e}", severity="warning")


if __name__ == "__main__":
    app = OpenCodeTUI()
    app.run()
