"""Pure-Pillow terminal/code screenshots.

Replaces the old Playwright/Chromium renderer: no browser binary, no OS
libraries, no cold-start cost -- which was the most common reason a deployed
instance silently produced reports with no images. Output looks like the
frontend's terminal window (dark body, traffic-light header).
"""

import io
import textwrap
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    "/Library/Fonts/Courier New.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
]

_BG = (30, 30, 30)
_HEADER = (45, 45, 45)
_FG = (212, 212, 212)
_DOTS = [(255, 95, 86), (255, 189, 46), (39, 201, 63)]

_FONT_SIZE = 15
_PAD = 16
_HEADER_H = 32
_LINE_SPACING = 4
_WRAP_COLUMNS = 80
_SCALE = 2  # render at 2x so the picture stays sharp inside a Word page

DEFAULT_OUTPUT_CHAR_LIMIT = 4_000
DEFAULT_OUTPUT_MAX_LINES = 45
DEFAULT_CODE_CHAR_LIMIT = 12_000
# Code longer than this is not screenshotted: a taller image can't fit a Word
# page, and the DOCX falls back to a text code block that paginates normally.
CODE_SCREENSHOT_MAX_LINES = 60


@lru_cache(maxsize=1)
def _font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = _FONT_SIZE * _SCALE
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    # Pillow >= 10.1 ships a scalable built-in font.
    try:
        return ImageFont.load_default(size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _prepare_lines(text: str, char_limit: int, max_lines: int = DEFAULT_OUTPUT_MAX_LINES) -> list[str]:
    truncated = False
    if len(text) > char_limit:
        text = text[:char_limit]
        truncated = True

    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\t", "    ").split("\n"):
        if not raw:
            lines.append("")
            continue
        # keep leading indentation when wrapping long lines
        indent = len(raw) - len(raw.lstrip(" "))
        wrapped = textwrap.wrap(
            raw,
            width=_WRAP_COLUMNS,
            subsequent_indent=" " * min(indent, 24),
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
        )
        lines.extend(wrapped or [""])

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    if truncated:
        lines.append("...[Output Truncated]")
    return lines or [""]


def render_terminal_png(
    text: str,
    char_limit: int = DEFAULT_OUTPUT_CHAR_LIMIT,
    max_lines: int = DEFAULT_OUTPUT_MAX_LINES,
) -> bytes:
    font = _font()
    lines = _prepare_lines(text, char_limit, max_lines)

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (_FONT_SIZE, 4)
    line_h = ascent + descent + _LINE_SPACING * _SCALE
    widest = max(probe.textlength(line, font=font) for line in lines)

    pad = _PAD * _SCALE
    header_h = _HEADER_H * _SCALE
    width = int(max(widest + 2 * pad, 420 * _SCALE))
    height = int(header_h + 2 * pad + line_h * len(lines))

    image = Image.new("RGB", (width, height), _BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, header_h], fill=_HEADER)
    radius = 6 * _SCALE
    for i, colour in enumerate(_DOTS):
        cx = pad + radius + i * (radius * 2 + 8 * _SCALE)
        cy = header_h // 2
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=colour)

    y = header_h + pad
    for line in lines:
        draw.text((pad, y), line, font=font, fill=_FG)
        y += line_h

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
