from rich.text import Text
from textual.widgets import Static

PREDICT_PRESETS = [0, 512, 1024, 2048, 4096, 8192, 16384]


class ContextBar(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.used = 0
        self.total = 4096
        self.model = ""
        self.show_thinking = True
        self.predict = 8192

    def set_usage(self, used: int, total: int, model: str = "") -> None:
        self.used = used
        self.total = total
        self.model = model
        self.refresh()

    def set_thinking_visible(self, visible: bool) -> None:
        self.show_thinking = visible
        self.refresh()

    def set_predict(self, predict: int) -> None:
        self.predict = predict
        self.refresh()

    def render(self) -> Text:
        if self.total == 0:
            return Text("")
        ratio = self.used / self.total
        bar_width = 20
        filled = min(int(ratio * bar_width), bar_width)
        empty = bar_width - filled

        blocks = "\u2583" * filled + "\u2591" * empty
        pct = ratio * 100

        if pct > 90:
            color = "#f38ba8"
        elif pct > 70:
            color = "#fab387"
        else:
            color = "#a6e3a1"

        used_label = f"{self.used:,}" if self.used >= 0 else "?"
        total_label = f"{self.total:,}"
        model_label = self.model.split(":")[0] if self.model else ""

        predict_label = f"PRED:{self.predict}" if self.predict > 0 else "PRED:\u221e"

        parts = [Text(" ")]
        if model_label:
            parts.append(Text(f"\u2502 {model_label} ", style="#585b70"))
        parts.append(Text(blocks, style=color))
        parts.append(Text(f" {pct:.0f}%", style="#6c7086"))
        parts.append(Text(f"  {used_label}/{total_label} ctx", style="#585b70"))
        parts.append(Text(f"  {predict_label}", style="#89b4fa"))
        parts.append(Text("  ", style="#585b70"))
        parts.append(Text("THK", style="#f5c2e7" if self.show_thinking else "#313244"))
        return Text.assemble(*parts)
