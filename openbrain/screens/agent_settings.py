from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select, Switch

from openbrain.utils import list_ollama_models


class AgentSettingsScreen(ModalScreen[dict]):
    def compose(self) -> ComposeResult:
        models = list_ollama_models()
        model_options = [(m, m) for m in models] if models else [("gemma4:e4b", "gemma4:e4b")]

        yield Container(
            Label("Sampling", classes="title"),
            Horizontal(Label("Temperature"), Input(id="temperature")),
            Horizontal(Label("Seed (-1 = random)"), Input(id="seed")),

            Label("Tool Enforcement", classes="title"),
            Horizontal(Label("Force tool use on first turn"), Switch(id="force_tool_use")),
            Horizontal(Label("Retry limit"), Input(id="force_tool_retry_limit")),

            Label("Calculate Guard", classes="title"),
            Horizontal(Label("Nudge after N calculate-only calls"), Switch(id="calc_guard_enabled")),
            Horizontal(Label("Threshold"), Input(id="calc_guard_threshold")),

            Label("Model Keep-Alive", classes="title"),
            Horizontal(Label("Keep-alive duration (e.g. 5m, 0)"), Input(id="keep_alive")),

            Label("Difficulty Routing (Benchmark only)", classes="title"),
            Horizontal(Label("Enable routing"), Switch(id="routing_enabled")),
            Horizontal(Label("Word threshold"), Input(id="routing_word_threshold")),
            Horizontal(Label("Keyword boost"), Switch(id="routing_keyword_boost")),
            Horizontal(Label("Hard model"), Select(model_options, id="hard_model")),

            Label("Ctrl+S to save, Escape to cancel", classes="hint"),
            classes="agent-settings-dialog",
        )

    def on_mount(self) -> None:
        cfg = self.app._cfg
        self.query_one("#temperature", Input).value = str(cfg.temperature)
        self.query_one("#seed", Input).value = str(cfg.seed)
        self.query_one("#force_tool_use", Switch).value = cfg.force_tool_use
        self.query_one("#force_tool_retry_limit", Input).value = str(cfg.force_tool_retry_limit)
        self.query_one("#calc_guard_enabled", Switch).value = cfg.calc_guard_enabled
        self.query_one("#calc_guard_threshold", Input).value = str(cfg.calc_guard_threshold)
        self.query_one("#keep_alive", Input).value = cfg.keep_alive
        self.query_one("#routing_enabled", Switch).value = cfg.routing_enabled
        self.query_one("#routing_word_threshold", Input).value = str(cfg.routing_word_threshold)
        self.query_one("#routing_keyword_boost", Switch).value = cfg.routing_keyword_boost
        try:
            self.query_one("#hard_model", Select).value = cfg.hard_model
        except Exception:
            pass

    def key_ctrl_s(self) -> None:
        self.dismiss({
            "temperature": float(self.query_one("#temperature", Input).value or 0.15),
            "seed": int(self.query_one("#seed", Input).value or -1),
            "force_tool_use": self.query_one("#force_tool_use", Switch).value,
            "force_tool_retry_limit": int(self.query_one("#force_tool_retry_limit", Input).value or 1),
            "calc_guard_enabled": self.query_one("#calc_guard_enabled", Switch).value,
            "calc_guard_threshold": int(self.query_one("#calc_guard_threshold", Input).value or 3),
            "keep_alive": self.query_one("#keep_alive", Input).value or "5m",
            "routing_enabled": self.query_one("#routing_enabled", Switch).value,
            "routing_word_threshold": int(self.query_one("#routing_word_threshold", Input).value or 200),
            "routing_keyword_boost": self.query_one("#routing_keyword_boost", Switch).value,
            "hard_model": str(self.query_one("#hard_model", Select).value or "gemma4:26b"),
        })

    def key_escape(self) -> None:
        self.dismiss(None)
