import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView

from openbrain.config import DATA_DIR


def _load_sessions() -> list[tuple[Path, dict]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for f in sorted(DATA_DIR.glob("session-*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            sessions.append((f, data))
        except Exception:
            pass
    return sessions


def _preview(data: dict) -> str:
    branches = data.get("branches", {})
    active = data.get("active_branch", "main")
    msgs = branches.get(active, [])
    count = len(msgs)
    preview = ""
    for m in msgs:
        if m.get("role") == "user":
            preview = m["content"][:60]
            break
    model = data.get("model", "?")
    return f"[bold]{model}[/]  {count} msg{'s' if count != 1 else ''}  {preview}"


class SessionListScreen(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Session History", classes="title"),
            ListView(id="session-list"),
            Label("\u2191\u2193 Navigate  Enter Load  Del Delete  Esc Close", classes="hint"),
            classes="session-dialog",
        )

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        lv = self.query_one("#session-list", ListView)
        lv.clear()
        sessions = _load_sessions()
        if not sessions:
            lv.mount(ListItem(Label("[dim italic]No saved sessions[/]")))
            return
        for path, data in sessions:
            ts = path.stem.replace("session-", "").replace("T", " ")
            preview = _preview(data)
            label = Label(f"{ts}\n    {preview}")
            item = ListItem(label)
            item.session_path = str(path)
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and hasattr(event.item, "session_path"):
            self.dismiss(event.item.session_path)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key == "delete":
            lv = self.query_one("#session-list", ListView)
            if lv.index is not None:
                item = lv.children[lv.index]
                if hasattr(item, "session_path"):
                    path = item.session_path
                    try:
                        Path(path).unlink(missing_ok=True)
                    except Exception:
                        pass
                    self._rebuild_list()
            event.stop()
