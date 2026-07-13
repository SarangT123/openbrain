from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView

from openbrain.utils import CONTEXT_PRESETS, list_ollama_models, ModelConfig


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
        self.models = list_ollama_models()
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
