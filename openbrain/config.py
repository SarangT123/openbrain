from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "openbrain"
CONFIG_PATH = CONFIG_DIR / "config.toml"
DATA_DIR = Path.home() / ".local" / "share" / "openbrain" / "sessions"
TEMPLATE_DIR = CONFIG_DIR / "templates"


@dataclass
class Config:
    default_model: str = ""
    default_ctx: int = 4096
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
