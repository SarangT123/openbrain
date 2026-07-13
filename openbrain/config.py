from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "openbrain"
CONFIG_PATH = CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "openbrain" / "sessions"
TEMPLATE_DIR = CONFIG_DIR / "templates"


DEFAULT_SYSTEM_PROMPT = """You are a precise AI coding assistant with access to tools. Follow these rules:

0. **Problem-solving method** — When solving math contest or algorithmic problems:
   a. Restate the problem in your own words to confirm understanding.
   b. Break it into small computational steps.
   c. Call a tool for every step — do not skip steps or rely on your own reasoning for computation.
   d. After getting an answer, verify it using a different tool or approach.
   e. Only then present the final answer.

1. **NEVER use web_search for math or contest problems** — `web_search` is strictly for looking up facts, documentation, news, definitions, or real-time information. Do NOT use it to find answers to math problems, contest problems, or puzzles. Using web_search for math is cheating and will produce wrong answers. Instead, use `calculate`, `sympy_calc`, `run_python`, `linear_algebra`, or `stats_calc`.

2. **Math & calculations** — Always use `calculate` for numerical expressions. Do NOT guess or compute from memory.

3. **Cross-checking** — Always verify your answers using a different tool when possible:
   - After `calculate`, verify with `run_python` or `sympy_calc`.
   - For probability, simulate with `run_python` (Monte Carlo) to verify.
   - For geometry, use coordinate geometry with `run_python`.
   - For combinatorics, enumerate small cases with `run_python` to confirm patterns.
   - Use multiple tools in a single turn for multi-part problems.

4. **Multiple tool calls** — Call several tools in one response. Break complex problems into steps and call a tool for each step.

5. **Tool choice**:
   - `calculate` — quick numeric expressions (arithmetic, trig, logs, constants)
   - `sympy_calc` — symbolic math (derivatives, integrals, solving equations, simplifying expressions)
   - `run_python` — brute force, enumeration, simulation, coordinate geometry, multi-step algorithms, verification
   - `web_search` — current information, facts, documentation, definitions (NOT for math problems)
   - `linear_algebra` — matrix operations
   - `stats_calc` — probability and statistics
   - `physics_constants` — physical constants lookup
   - `unit_converter` — unit conversion

6. **Example patterns**:
   - Geometry: place coordinates, compute with `run_python` (e.g., shoelace formula, distance, dot products)
   - Probability: derive analytically, then simulate with `run_python` to verify
   - Number theory: use `run_python` to enumerate small cases, look for patterns, then generalize
   - Algebra: simplify with `sympy_calc`, evaluate with `calculate`, verify with `run_python`
"""


@dataclass
class Config:
    default_model: str = ""
    default_ctx: int = 4096
    default_predict: int = 8192
    system_prompt: str = ""
    save_history: bool = True
    auto_restore: bool = True
    show_thinking: bool = True

    # --- sampling ---
    temperature: float = 0.15
    seed: int = -1

    # --- tool enforcement ---
    force_tool_use: bool = True
    force_tool_retry_limit: int = 1

    # --- calculate guard ---
    calc_guard_enabled: bool = True
    calc_guard_threshold: int = 3

    # --- model / VRAM management ---
    keep_alive: str = "5m"
    easy_model: str = "gemma4:e4b"
    hard_model: str = "gemma4:26B"

    # --- self-consistency ---
    self_consistency_n_easy: int = 3
    self_consistency_n_hard: int = 1

    # --- difficulty routing ---
    routing_enabled: bool = False
    routing_word_threshold: int = 200
    routing_keyword_boost: bool = True

    # --- benchmark / grading ---
    question_bank_path: str = "benchmarks/questions.json"
    answer_key_path: str = "benchmarks/answers.json"
    auto_grade: bool = False


def load_config() -> Config:
    import tomllib

    cfg = Config()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "rb") as f:
                data = tomllib.load(f)
            cfg.default_model = data.get("model", "")
            cfg.default_ctx = data.get("num_ctx", 4096)
            cfg.default_predict = data.get("num_predict", 8192)
            cfg.system_prompt = data.get("system_prompt", "")
            cfg.save_history = data.get("save_history", True)
            cfg.auto_restore = data.get("auto_restore", True)
            cfg.show_thinking = data.get("show_thinking", True)
            cfg.temperature = data.get("temperature", 0.15)
            cfg.seed = data.get("seed", -1)
            cfg.force_tool_use = data.get("force_tool_use", True)
            cfg.force_tool_retry_limit = data.get("force_tool_retry_limit", 1)
            cfg.calc_guard_enabled = data.get("calc_guard_enabled", True)
            cfg.calc_guard_threshold = data.get("calc_guard_threshold", 3)
            cfg.keep_alive = data.get("keep_alive", "5m")
            cfg.easy_model = data.get("easy_model", "gemma4:e4b")
            cfg.hard_model = data.get("hard_model", "gemma4:26B")
            cfg.self_consistency_n_easy = data.get("self_consistency_n_easy", 3)
            cfg.self_consistency_n_hard = data.get("self_consistency_n_hard", 1)
            cfg.routing_enabled = data.get("routing_enabled", False)
            cfg.routing_word_threshold = data.get("routing_word_threshold", 200)
            cfg.routing_keyword_boost = data.get("routing_keyword_boost", True)
            cfg.question_bank_path = data.get("question_bank_path", "benchmarks/questions.json")
            cfg.answer_key_path = data.get("answer_key_path", "benchmarks/answers.json")
            cfg.auto_grade = data.get("auto_grade", False)
        except Exception:
            pass
    else:
        save_config_to_disk(cfg)
    return cfg


def save_config_to_disk(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f'model = "{cfg.default_model}"',
        f"num_ctx = {cfg.default_ctx}",
        f"num_predict = {cfg.default_predict}",
    ]
    if cfg.system_prompt:
        esc = cfg.system_prompt.replace('"', '\\"')
        lines.append(f'system_prompt = "{esc}"')
    else:
        lines.append('system_prompt = ""')
    lines.append(f"save_history = {'true' if cfg.save_history else 'false'}")
    lines.append(f"auto_restore = {'true' if cfg.auto_restore else 'false'}")
    lines.append(f"show_thinking = {'true' if cfg.show_thinking else 'false'}")
    lines.append(f"temperature = {cfg.temperature}")
    lines.append(f"seed = {cfg.seed}")
    lines.append(f"force_tool_use = {'true' if cfg.force_tool_use else 'false'}")
    lines.append(f"force_tool_retry_limit = {cfg.force_tool_retry_limit}")
    lines.append(f"calc_guard_enabled = {'true' if cfg.calc_guard_enabled else 'false'}")
    lines.append(f"calc_guard_threshold = {cfg.calc_guard_threshold}")
    lines.append(f'keep_alive = "{cfg.keep_alive}"')
    lines.append(f'easy_model = "{cfg.easy_model}"')
    lines.append(f'hard_model = "{cfg.hard_model}"')
    lines.append(f"self_consistency_n_easy = {cfg.self_consistency_n_easy}")
    lines.append(f"self_consistency_n_hard = {cfg.self_consistency_n_hard}")
    lines.append(f"routing_enabled = {'true' if cfg.routing_enabled else 'false'}")
    lines.append(f"routing_word_threshold = {cfg.routing_word_threshold}")
    lines.append(f"routing_keyword_boost = {'true' if cfg.routing_keyword_boost else 'false'}")
    lines.append(f'question_bank_path = "{cfg.question_bank_path}"')
    lines.append(f'answer_key_path = "{cfg.answer_key_path}"')
    lines.append(f"auto_grade = {'true' if cfg.auto_grade else 'false'}")
    CONFIG_PATH.write_text("\n".join(lines) + "\n")
