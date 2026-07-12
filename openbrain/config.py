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
    CONFIG_PATH.write_text("\n".join(lines) + "\n")
