from rich.console import Group
from rich.markdown import Markdown
from rich.text import Text
from textual.widgets import Static

from openbrain.utils import preprocess_math


class ChatMessage(Static):
    def __init__(self, content: str, role: str, model: str = "", thinking: str = "", show_thinking: bool = True, is_thinking: bool = False) -> None:
        self.role = role
        self.model = model
        self._thinking = thinking
        self._show_thinking = show_thinking
        self._is_thinking = is_thinking
        super().__init__(content)

    def update_content(self, content: str, thinking: str = "", show_thinking: bool | None = None, is_thinking: bool = False) -> None:
        super().update(content)
        self._thinking = thinking
        self._is_thinking = is_thinking
        if show_thinking is not None:
            self._show_thinking = show_thinking
        self.refresh()

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

        elements: list[Text | Markdown] = [
            Text.assemble(
                Text(" \u2502 ", style="#585b70"),
                Text(label, style="bold #a6e3a1"),
            ),
        ]
        if self._show_thinking and self._thinking:
            elements.append(Text(f" {self._thinking}", style="dim italic #6c7086"))
        elif self._is_thinking:
            elements.append(Text(" Reasoning...", style="dim #585b70"))
        if display:
            elements.append(Markdown(display, code_theme="catppuccin-frappe"))
        return Group(*elements)
