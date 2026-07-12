import json

from rich.console import Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.text import Text
from textual import events
from textual.widgets import Static
from textual_image.widget import AutoRenderable

from openbrain.utils import make_image_renderable, preprocess_math


def _indent(renderable: object) -> Padding:
    return Padding(renderable, (0, 0, 0, 4))


class ChatMessage(Static):
    can_focus = True

    def __init__(self, content: str, role: str, model: str = "", thinking: str = "", show_thinking: bool = True, is_thinking: bool = False, images: list[str] | None = None, tool_calls: list[dict] | None = None) -> None:
        self.role = role
        self.model = model
        self._thinking = thinking
        self._show_thinking = show_thinking
        self._is_thinking = is_thinking
        self._images = images or []
        self._show_source = False
        self._tool_calls = [
            {**tc, "status": "done"}
            for tc in (tool_calls or [])
        ]
        self._thinking_expanded = False
        super().__init__(content)
        self.add_class(role)

    def update_content(self, content: str, thinking: str = "", show_thinking: bool | None = None, is_thinking: bool = False) -> None:
        super().update(content)
        self._thinking = thinking
        self._is_thinking = is_thinking
        if show_thinking is not None:
            self._show_thinking = show_thinking
        self._show_source = False
        self.refresh()

    def add_tool_call(self, name: str, args: dict) -> None:
        self._tool_calls.append({"name": name, "args": args, "status": "running"})
        self.refresh()

    def set_tool_done(self, name: str) -> None:
        for tc in self._tool_calls:
            if tc["name"] == name and tc["status"] == "running":
                tc["status"] = "done"
        self.refresh()

    async def on_click(self, event: events.Click) -> None:
        if self.role != "assistant":
            return
        if self._thinking and not self._is_thinking:
            self._thinking_expanded = not self._thinking_expanded
            self.refresh(layout=True)
            self.scroll_visible()
        elif "$$" in self.content:
            self._show_source = not self._show_source
            self.refresh(layout=True)
            self.scroll_visible()

    def render(self) -> Text | Group:
        text = str(self.content)
        if self.role == "user":
            elements: list = [
                Text.assemble(Text("  "), Text("you", style="bold #89b4fa")),
            ]
            spacer = False
            if self._images:
                img = make_image_renderable(self._images[0])
                if img:
                    elements.append(Text(""))
                    elements.append(_indent(img))
                    spacer = True
            if text:
                if not spacer:
                    elements.append(Text(""))
                elements.append(_indent(Text(f"{text}", style="#cdd6f4")))
            return Group(*elements)

        label = self.model or "assistant"
        elements: list = [
            Text.assemble(Text("  "), Text(label, style="bold #a6e3a1")),
        ]
        has_section = False
        if self._is_thinking and self._thinking:
            elements.append(Text(""))
            elements.append(_indent(Markdown(self._thinking, style="dim #585b70")))
            has_section = True
        elif self._is_thinking:
            elements.append(Text(""))
            elements.append(_indent(Text("\U0001f4ad  Thinking...", style="dim #585b70")))
            has_section = True
        elif self._show_thinking and self._thinking:
            elements.append(Text(""))
            if self._thinking_expanded:
                elements.append(_indent(Markdown(self._thinking, style="dim")))
            else:
                elements.append(_indent(Text("\U0001f4ad  Thought", style="dim #585b70")))
            has_section = True
        if self._tool_calls:
            if not has_section:
                elements.append(Text(""))
            for tc in self._tool_calls:
                icon = "\U0001f50d" if tc["status"] == "running" else "\u2705"
                color = "#f9e2af" if tc["status"] == "running" else "#a6e3a1"
                args_str = json.dumps(tc["args"])
                elements.append(_indent(Text(f"{icon}  {tc['name']}({args_str})", style=color)))
            has_section = True
        if text:
            if not has_section:
                elements.append(Text(""))
            segments = preprocess_math(text)
            for seg in segments:
                if seg["type"] == "latex" and self._show_source:
                    elements.append(_indent(Text(f"$$ {seg['source']} $$", style="italic #f9e2af")))
                else:
                    elements.append(_indent(seg["renderable"]))
        return Group(*elements)
