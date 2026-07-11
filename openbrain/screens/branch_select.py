from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


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
