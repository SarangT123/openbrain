import base64
import io
import re
import subprocess
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage
from pylatexenc.latex2text import LatexNodes2Text
from rich.markdown import Markdown
from textual_image.widget import AutoRenderable

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


def _render_latex_image(expr: str) -> AutoRenderable | None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    try:
        dpi = 150
        fig, ax = plt.subplots(figsize=(0.01, 0.01))
        ax.axis('off')
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        ax.text(0.5, 0.5, f'${expr}$', fontsize=16,
                color='#cdd6f4', ha='center', va='center',
                transform=ax.transAxes)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                    pad_inches=0.08, transparent=True)
        plt.close(fig)
        buf.seek(0)
        pil = PILImage.open(buf)
        return AutoRenderable(pil)
    except Exception:
        return None


def preprocess_math(text: str) -> list[dict]:
    segments: list[dict] = []
    pos = 0
    for m in re.finditer(r"\$\$(.+?)\$\$", text, re.DOTALL):
        before = text[pos:m.start()]
        if before:
            before = re.sub(r"\$(.+?)\$", _latex_to_text, before)
            segments.append({"type": "text", "renderable": Markdown(before, code_theme="catppuccin-frappe")})
        source = m.group(1)
        img = _render_latex_image(source)
        if img is not None:
            segments.append({"type": "latex", "renderable": img, "source": source})
        else:
            converted = _LATEX_CONVERTER.latex_to_text(source)
            segments.append({"type": "text", "renderable": Markdown(f"`{converted}`", code_theme="catppuccin-frappe")})
        pos = m.end()
    remaining = text[pos:]
    if remaining:
        remaining = re.sub(r"\$(.+?)\$", _latex_to_text, remaining)
        segments.append({"type": "text", "renderable": Markdown(remaining, code_theme="catppuccin-frappe")})
    if not segments:
        text = re.sub(r"\$(.+?)\$", _latex_to_text, text)
        segments.append({"type": "text", "renderable": Markdown(text, code_theme="catppuccin-frappe")})
    return segments


def read_image_from_clipboard() -> bytes | None:
    for cmd in (
        ["wl-paste", "--type", "image/png"],
        ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"],
    ):
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except FileNotFoundError:
            pass
    return None


def image_path_to_base64(path: str) -> str | None:
    try:
        data = Path(path).read_bytes()
        return base64.b64encode(data).decode()
    except Exception:
        return None


def format_image_info(path: str = "", size: int = 0) -> str:
    label = path or "clipboard"
    kb = size / 1024
    return f"{label}  ({kb:.0f} KB)" if kb < 1024 else f"{label}  ({kb / 1024:.1f} MB)"


def make_image_renderable(b64_data: str) -> object | None:
    try:
        raw = base64.b64decode(b64_data)
        pil = PILImage.open(io.BytesIO(raw))
        return AutoRenderable(pil)
    except Exception:
        return None


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
