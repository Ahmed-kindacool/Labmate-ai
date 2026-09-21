from playwright.async_api import async_playwright

from app.screenshots.service import ScreenshotService
from app.screenshots.terminal_renderer import render_terminal_html

__all__ = ["ScreenshotService", "generate_terminal_screenshot"]


async def generate_terminal_screenshot(output: str) -> bytes:
    """Original single-shot API (Dev C, Phase 5): renders one terminal
    screenshot, launching and tearing down its own browser. Kept for
    compatibility/standalone use; GenerationService uses ScreenshotService
    instead, which reuses one browser across a whole report's screenshots.
    """
    html_content = render_terminal_html(output)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.set_content(html_content)

            terminal_element = page.locator("#terminal")
            return await terminal_element.screenshot()
        finally:
            await browser.close()
