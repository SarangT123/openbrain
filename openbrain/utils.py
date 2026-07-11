import re
import subprocess
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

from pylatexenc.latex2text import LatexNodes2Text

from openbrain.config import CONFIG_DIR, TEMPLATE_DIR


def copy_to_clipboard(text: str) -> bool:
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "-i", "-b"]):
        try:
            subprocess.run(cmd, input=text, text=True, timeout=2, capture_output=True)
            return True
        except FileNotFoundError:
            pass
    return False


CONTEXT_PRESETS = [2048, 4096, 8192, 16384, 32768, 65536, 131072]


@dataclass
class ModelConfig:
    model: str
    num_ctx: int = 4096


def make_message(role: str, content: str, **kw) -> dict:
    msg = {"id": uuid.uuid4().hex[:12], "role": role, "content": content}
    msg.update(kw)
    return msg


_LATEX_CONVERTER = LatexNodes2Text()


def _latex_to_text(match: re.Match) -> str:
    raw = match.group(1)
    try:
        converted = _LATEX_CONVERTER.latex_to_text(raw)
    except Exception:
        converted = raw
    return f"`{converted}`"


def preprocess_math(text: str) -> str:
    text = re.sub(r"\$\$(.+?)\$\$", _latex_to_text, text, flags=re.DOTALL)
    text = re.sub(r"\$(.+?)\$", _latex_to_text, text)
    return text


def load_templates() -> list[tuple[str, str]]:
    if not TEMPLATE_DIR.is_dir():
        return []
    result = []
    for f in sorted(TEMPLATE_DIR.iterdir()):
        if f.suffix in (".txt", ".toml", ".md"):
            try:
                content = f.read_text().strip()
                name = f.stem.replace("_", " ").replace("-", " ").title()
                if f.suffix == ".toml":
                    try:
                        data = tomllib.loads(content)
                        name = data.get("name", name)
                        content = data.get("prompt", content)
                    except Exception:
                        pass
                result.append((name, content))
            except Exception:
                pass
    return result
