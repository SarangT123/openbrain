import csv
import json
import re
from datetime import datetime
from pathlib import Path

from openbrain.agent import run_agent_turn
from openbrain.grading import grade_answer
from openbrain.routing import pick_model
from openbrain.tools import TOOLS

BENCHMARKS_DIR = Path("benchmarks")
BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)


def _extract_final_answer(text: str) -> str:
    matches = re.findall(r"\b(\d{1,3})\b", text)
    return matches[-1] if matches else ""


def _save_session(q_id: str, model: str, votes: list[str], majority: str) -> None:
    path = BENCHMARKS_DIR / f"session-{datetime.now():%Y%m%d-%H%M%S}-{q_id}.json"
    data = {
        "q_id": q_id,
        "model": model,
        "votes": votes,
        "majority": majority,
        "timestamp": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(data, indent=2))


def _append_to_benchmark_csv(q_id: str, model: str, answer: str, correct: bool) -> None:
    csv_path = BENCHMARKS_DIR / "benchmark.csv"
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["QN", "Model", "AI ans", "Correct", "RIGHT?WRONG"])
        writer.writerow([q_id, model, answer, answer, 1 if correct else 0])


async def run_benchmark_suite(cfg, client):
    with open(cfg.question_bank_path) as f:
        questions = json.load(f)

    answer_key = {}
    if cfg.auto_grade:
        with open(cfg.answer_key_path) as f:
            answer_key = json.load(f)

    batches: dict[str, list[dict]] = {}
    for q in questions:
        model = pick_model(q["question"], cfg)
        batches.setdefault(model, []).append(q)

    for model, batch in batches.items():
        yield f"[bold]Switching to {model}[/bold] — {len(batch)} question(s)"
        n_votes = cfg.self_consistency_n_hard if model == cfg.hard_model else cfg.self_consistency_n_easy

        for q in batch:
            votes = []
            for i in range(n_votes):
                try:
                    result = await run_agent_turn(
                        client, model,
                        messages=[{"role": "user", "content": q["question"]}],
                        tools=TOOLS,
                        temperature=cfg.temperature,
                        seed=cfg.seed,
                        keep_alive=cfg.keep_alive,
                        force_tool_use=cfg.force_tool_use,
                        force_tool_retry_limit=cfg.force_tool_retry_limit,
                        calc_guard_enabled=cfg.calc_guard_enabled,
                        calc_guard_threshold=cfg.calc_guard_threshold,
                    )
                except Exception as e:
                    yield f"  [red]ERROR on {q['id']}[/red]: {e}"
                    votes.append("")
                    continue

                answer = _extract_final_answer(result.final_text)
                votes.append(answer)
                yield f"  {q['id']} vote {i+1}/{n_votes}: {answer}"

            majority = max(set(votes), key=votes.count) if votes else ""
            _save_session(q["id"], model, votes, majority)

            if cfg.auto_grade and q["id"] in answer_key:
                correct = grade_answer(majority, answer_key[q["id"]])
                _append_to_benchmark_csv(q["id"], model, majority, correct)
                mark = "[green]✓[/green]" if correct else "[red]✗[/red]"
                yield f"  {q['id']}: {mark} (majority={majority}, expected={answer_key[q['id']]})"
