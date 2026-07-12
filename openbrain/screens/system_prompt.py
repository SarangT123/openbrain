from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, TextArea

from openbrain.config import DEFAULT_SYSTEM_PROMPT


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
        text = app.system_prompt if (hasattr(app, "system_prompt") and app.system_prompt) else DEFAULT_SYSTEM_PROMPT
        self.query_one("#sys-prompt-editor", TextArea).text = text
        self.query_one("#sys-prompt-editor", TextArea).focus()

    def on_text_area_changed(self, _) -> None:
        pass

    def key_escape(self) -> None:
        app = self.app
        self.dismiss(app.system_prompt if hasattr(app, "system_prompt") else "")

    def key_ctrl_s(self) -> None:
        self.dismiss(self.query_one("#sys-prompt-editor", TextArea).text)
