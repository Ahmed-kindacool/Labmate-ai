from app.screenshots.image_renderer import (
    CODE_SCREENSHOT_MAX_LINES,
    DEFAULT_CODE_CHAR_LIMIT,
    render_terminal_png,
)
from app.screenshots.service import ScreenshotService

__all__ = ["ScreenshotService", "generate_terminal_screenshot", "generate_code_screenshot"]


async def generate_terminal_screenshot(output: str) -> bytes:
    """Renders terminal output as a PNG (pure Pillow, no browser needed)."""
    import asyncio

    return await asyncio.to_thread(render_terminal_png, output)


async def generate_code_screenshot(code: str) -> bytes:
    """Same window style, but with a much higher truncation limit so source
    code isn't cut off at the output limit. Callers should skip code longer
    than CODE_SCREENSHOT_MAX_LINES (see GenerationService)."""
    import asyncio

    return await asyncio.to_thread(
        render_terminal_png, code, DEFAULT_CODE_CHAR_LIMIT, CODE_SCREENSHOT_MAX_LINES
    )
