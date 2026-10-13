import asyncio

from app.schemas.generate import TaskExecutionResult
from app.schemas.lab import ExecutionStatus
from app.screenshots.image_renderer import render_terminal_png

# Which outcomes get a screenshot at all. Per AI_AND_GENERATION.md's
# anti-fabrication rule, SUCCESS and FAILED/TIMEOUT are all real outcomes worth
# showing (stdout for success, stderr for the others). UNSUPPORTED means nothing
# genuinely ran, so there is no real output to screenshot.
_CAPTURABLE_STATUSES = {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT}


class ScreenshotService:
    """Renders terminal-style PNGs of real execution output (pure Pillow)."""

    async def capture_many(self, execution_results: list[TaskExecutionResult]) -> dict[str, bytes]:
        screenshots: dict[str, bytes] = {}
        for item in execution_results:
            if item.result.status not in _CAPTURABLE_STATUSES:
                continue
            text = (
                item.result.stdout
                if item.result.status == ExecutionStatus.SUCCESS
                else item.result.stderr
            )
            # A program that printed nothing is still a real outcome.
            screenshots[item.task_id] = await asyncio.to_thread(
                render_terminal_png, text if text.strip() else "(no terminal output)"
            )
        return screenshots
