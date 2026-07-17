from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView

from openbrain.config import SYSTEM_PROMPT_PRESETS


class PromptPresetScreen(ModalScreen[str | None]):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("System prompt presets", classes="title"),
            ListView(id="preset-list"),
            Label("Enter to select, Escape to cancel", classes="hint"),
            classes="template-dialog",
        )

    def on_mount(self) -> None:
        lv = self.query_one("#preset-list", ListView)
        for name, _ in SYSTEM_PROMPT_PRESETS:
            item = ListItem(Label(name))
            item.preset_name = name
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item:
            self.dismiss(event.item.preset_name)

    def key_escape(self) -> None:
        self.dismiss(None)
