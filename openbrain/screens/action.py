from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


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
            ("agent_settings", "Agent Settings"),
            ("system_prompt", "Edit System Prompt"),
            ("prompt_presets", "Prompt Presets"),
            ("benchmark", "Run Benchmark"),
            ("sessions", "Session History"),
            ("new_session", "New Session"),
        ]:
            item = ListItem(Label(label))
            item.action_name = action
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item:
            self.dismiss(event.item.action_name)
