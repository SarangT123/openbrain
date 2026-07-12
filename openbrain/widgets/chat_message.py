from rich.console import Group
from rich.markdown import Markdown
from rich.text import Text
from textual import events
from textual.widgets import Static
from textual_image.widget import AutoRenderable

from openbrain.utils import make_image_renderable, preprocess_math


class ChatMessage(Static):
    def __init__(self, content: str, role: str, model: str = "", thinking: str = "", show_thinking: bool = True, is_thinking: bool = False, images: list[str] | None = None) -> None:
        self.role = role
        self.model = model
        self._thinking = thinking
        self._show_thinking = show_thinking
        self._is_thinking = is_thinking
        self._images = images or []
        self._show_source = False
        super().__init__(content)

    def update_content(self, content: str, thinking: str = "", show_thinking: bool | None = None, is_thinking: bool = False) -> None:
        super().update(content)
        self._thinking = thinking
        self._is_thinking = is_thinking
        if show_thinking is not None:
            self._show_thinking = show_thinking
        self._show_source = False
        self.refresh()

    def on_click(self, event: events.Click) -> None:
        if self.role != "assistant" or "$$" not in self.content:
            return
        self._show_source = not self._show_source
        self.refresh()

    def render(self) -> Text | Group:
        text = str(self.content)
        if self.role == "user":
            parts = [
                Text(" \u2502 ", style="#585b70"),
                Text("you", style="bold #89b4fa"),
            ]
            elements: list[Text | Markdown | Group | AutoRenderable] = [
                Text.assemble(*parts),
            ]
            if self._images:
                img_render = make_image_renderable(self._images[0])
                if img_render:
                    elements.append(img_render)
                    elements.append(Text(""))
            if text:
                elements.append(Text(f" {text}", style="#cdd6f4"))
            return Group(*elements) if len(elements) > 1 else Text.assemble(*parts, Text(f" {text}", style="#cdd6f4")) if text else Text.assemble(*parts)

        label = self.model or "assistant"
        elements: list[Text | Markdown | AutoRenderable] = [
            Text.assemble(
                Text(" \u2502 ", style="#585b70"),
                Text(label, style="bold #a6e3a1"),
            ),
        ]
        if self._show_thinking and self._thinking:
            elements.append(Text(f" {self._thinking}", style="dim italic #6c7086"))
        elif self._is_thinking:
            elements.append(Text(" Reasoning...", style="dim #585b70"))
        if text:
            segments = preprocess_math(text)
            for seg in segments:
                if seg["type"] == "latex" and self._show_source:
                    elements.append(Text(f"$${seg['source']}$$", style="italic #f9e2af"))
                else:
                    elements.append(seg["renderable"])
        return Group(*elements)
