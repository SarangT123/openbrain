from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView


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
