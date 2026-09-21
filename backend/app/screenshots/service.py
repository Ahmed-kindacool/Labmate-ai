from playwright.async_api import Browser, async_playwright

from app.schemas.generate import TaskExecutionResult
from app.schemas.lab import ExecutionStatus
from app.screenshots.terminal_renderer import render_terminal_html

# Which outcomes get a screenshot at all. Per AI_AND_GENERATION.md's
# anti-fabrication rule ("report the actual failure or omit the
# screenshot"), SUCCESS and FAILED/TIMEOUT are all real, non-fabricated
# outcomes worth showing — stdout for success, stderr (the actual error
# text) for the others. UNSUPPORTED means nothing genuinely ran (execution
# disabled, unavailable, or the language isn't supported), so there is no
# real output to screenshot — that's a text note in the DOCX (Phase 7),
# not an image.
_CAPTURABLE_STATUSES = {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT}


class ScreenshotService:
    """Captures terminal-style PNG screenshots of real execution output.

    Launches exactly one Chromium instance per `capture_many()` call and
    reuses it across every task in the report — a report with several
    executed tasks would otherwise pay a full browser-startup cost
    (seconds) per task, which is the dominant cost of this whole step.
    """

    async def capture_many(
        self, execution_results: list[TaskExecutionResult]
    ) -> dict[str, bytes]:
        capturable = [r for r in execution_results if r.result.status in _CAPTURABLE_STATUSES]
        if not capturable:
            return {}

        screenshots: dict[str, bytes] = {}
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                for item in capturable:
                    screenshots[item.task_id] = await self._capture_one(browser, item)
            finally:
                await browser.close()
        return screenshots

    async def _capture_one(self, browser: Browser, item: TaskExecutionResult) -> bytes:
        text = (
            item.result.stdout
            if item.result.status == ExecutionStatus.SUCCESS
            else item.result.stderr
        )
        html_content = render_terminal_html(text)

        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.set_content(html_content)
            terminal_element = page.locator("#terminal")
            return await terminal_element.screenshot()
        finally:
            await context.close()
