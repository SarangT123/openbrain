from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class RenameSessionScreen(ModalScreen[str | None]):
    def __init__(self, current_name: str):
        super().__init__()
        self.current_name = current_name

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Rename Session", classes="title"),
            Input(value=self.current_name, placeholder="Enter a name...", id="rename-input"),
            Label("Enter to confirm  Esc to cancel", classes="hint"),
            classes="rename-dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#rename-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        self.dismiss(name if name else None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
