import json

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RichLog, Static, Switch

from openbrain.config import save_config_to_disk


class BenchmarkScreen(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Benchmark Run", classes="title"),
            Horizontal(Label("Question bank path"), Input(id="question_bank_path")),
            Horizontal(Label("Answer key path"), Input(id="answer_key_path")),

            Label("Self-Consistency (votes per question)", classes="title"),
            Horizontal(Label("N for easy model"), Input(id="self_consistency_n_easy")),
            Horizontal(Label("N for hard model"), Input(id="self_consistency_n_hard")),

            Horizontal(Label("Auto-grade after run"), Switch(id="auto_grade")),
            Horizontal(
                Button("Run Benchmark", id="run-btn", variant="primary"),
                Button("Close", id="close-btn"),
            ),
            Label("Now solving:", classes="title"),
            Static("", id="bench-live"),
            RichLog(id="bench-log", markup=True),
            classes="benchmark-dialog",
        )

    def on_mount(self) -> None:
        cfg = self.app._cfg
        self.query_one("#question_bank_path", Input).value = cfg.question_bank_path
        self.query_one("#answer_key_path", Input).value = cfg.answer_key_path
        self.query_one("#self_consistency_n_easy", Input).value = str(cfg.self_consistency_n_easy)
        self.query_one("#self_consistency_n_hard", Input).value = str(cfg.self_consistency_n_hard)
        self.query_one("#auto_grade", Switch).value = cfg.auto_grade

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self._save_fields()
            self.dismiss(None)
        elif event.button.id == "run-btn":
            self._save_fields()
            self.run_worker(self._run_benchmark(), exclusive=True)

    def _save_fields(self) -> None:
        cfg = self.app._cfg
        cfg.question_bank_path = self.query_one("#question_bank_path", Input).value
        cfg.answer_key_path = self.query_one("#answer_key_path", Input).value
        cfg.self_consistency_n_easy = int(self.query_one("#self_consistency_n_easy", Input).value or 1)
        cfg.self_consistency_n_hard = int(self.query_one("#self_consistency_n_hard", Input).value or 1)
        cfg.auto_grade = self.query_one("#auto_grade", Switch).value
        save_config_to_disk(cfg)

    async def _run_benchmark(self) -> None:
        log = self.query_one("#bench-log", RichLog)
        live = self.query_one("#bench-live", Static)
        cfg = self.app._cfg
        from openbrain.benchmark_runner import run_benchmark_suite

        def on_chunk(content: str, thinking: str) -> None:
            text = content or thinking
            live.update(text[-800:])

        def on_tool_call(tc: dict) -> None:
            current = str(live.renderable or "")
            live.update(f"[calling {tc.get('name', '?')}...]\n{current[-700:]}")

        try:
            async for line in run_benchmark_suite(cfg, self.app.client, on_chunk=on_chunk, on_tool_call=on_tool_call):
                if line == "__CLEAR_LIVE__":
                    live.update("")
                else:
                    log.write(line)
        except FileNotFoundError as e:
            log.write(f"[red]ERROR: File not found: {e}[/red]")
            log.write("[yellow]Ensure benchmarks/questions.json and benchmarks/answers.json exist.[/yellow]")
        except json.JSONDecodeError as e:
            log.write(f"[red]ERROR: Invalid JSON in question bank or answer key: {e}[/red]")
        except Exception as e:
            log.write(f"[red]ERROR: {e}[/red]")
