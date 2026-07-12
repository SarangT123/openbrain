import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView

from openbrain.config import DATA_DIR
from openbrain.screens.rename_session import RenameSessionScreen


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


def _format_entry(data: dict) -> str:
    name = data.get("name") or "Untitled"
    ts = data.get("timestamp", "")
    if ts:
        try:
            ts = ts[:16].replace("T", " ")
        except Exception:
            pass
    model = data.get("model", "?")
    branches = data.get("branches", {})
    active = data.get("active_branch", "main")
    msgs = branches.get(active, [])
    count = len(msgs)

    first_user = ""
    for m in msgs:
        if m.get("role") == "user":
            first_user = m["content"][:55].replace("\n", " ")
            break

    lines = [f"[bold]{name}[/]"]
    lines.append(f"  {ts}  |  {model}  |  {count} msg{'s' if count != 1 else ''}")
    if first_user:
        lines.append(f"  {first_user}")
    return "\n".join(lines)


class SessionListScreen(ModalScreen[str | None]):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Session History", classes="title"),
            ListView(id="session-list"),
            Label(
                "\u2191\u2193 Navigate  Enter Load  r Rename  Del Delete  Esc Close",
                classes="hint",
            ),
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
            label = Label(_format_entry(data))
            item = ListItem(label)
            item.session_path = str(path)
            item.session_data = data
            lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and hasattr(event.item, "session_path"):
            self.dismiss(event.item.session_path)

    def _selected_item(self):
        lv = self.query_one("#session-list", ListView)
        if lv.index is not None and lv.children:
            item = lv.children[lv.index]
            if hasattr(item, "session_path"):
                return item
        return None

    def _rename_selected(self) -> None:
        item = self._selected_item()
        if not item:
            return
        current_name = item.session_data.get("name") or "Untitled"
        self.push_screen(
            RenameSessionScreen(current_name),
            callback=lambda new_name: self._on_rename_done(item, new_name),
        )

    def _on_rename_done(self, item, new_name: str | None) -> None:
        if not new_name:
            return
        try:
            path = Path(item.session_path)
            data = json.loads(path.read_text())
            data["name"] = new_name
            path.write_text(json.dumps(data, indent=2))
            self._rebuild_list()
        except Exception:
            pass

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key == "delete":
            item = self._selected_item()
            if item:
                try:
                    Path(item.session_path).unlink(missing_ok=True)
                except Exception:
                    pass
                self._rebuild_list()
            event.stop()
        elif event.key == "r":
            self._rename_selected()
            event.stop()
