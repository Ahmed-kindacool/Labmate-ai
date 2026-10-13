import io

import pytest
from PIL import Image

from app.schemas.generate import TaskExecutionResult
from app.schemas.lab import ExecutionResult, ExecutionStatus
from app.screenshots import generate_code_screenshot, generate_terminal_screenshot
from app.screenshots.image_renderer import _prepare_lines, render_terminal_png
from app.screenshots.service import ScreenshotService


def _image(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png))


def _result(status: ExecutionStatus, stdout: str = "", stderr: str = "") -> ExecutionResult:
    return ExecutionResult(status=status, stdout=stdout, stderr=stderr, exit_code=0)


class TestRenderer:
    def test_produces_a_real_png(self) -> None:
        png = render_terminal_png("hello world")
        assert png.startswith(b"\x89PNG")
        image = _image(png)
        assert image.width > 100 and image.height > 50

    def test_longer_output_makes_a_taller_image(self) -> None:
        short = _image(render_terminal_png("a"))
        tall = _image(render_terminal_png("\n".join(["line"] * 20)))
        assert tall.height > short.height

    def test_long_lines_are_wrapped_not_infinitely_wide(self) -> None:
        image = _image(render_terminal_png("x" * 5000))
        assert image.width < 3000

    def test_truncates_over_the_char_limit(self) -> None:
        lines = _prepare_lines("x" * 5000, 4000)
        assert lines[-1] == "...[Output Truncated]"

    def test_short_output_is_not_truncated(self) -> None:
        assert "Truncated" not in "".join(_prepare_lines("hello", 4000))

    def test_empty_and_unicode_text_do_not_crash(self) -> None:
        assert render_terminal_png("").startswith(b"\x89PNG")
        assert render_terminal_png("héllo → ✓ 日本").startswith(b"\x89PNG")

    @pytest.mark.asyncio
    async def test_async_helpers(self) -> None:
        assert (await generate_terminal_screenshot("hi")).startswith(b"\x89PNG")
        code = "\n".join(f"print({i})" for i in range(40))
        assert (await generate_code_screenshot(code)).startswith(b"\x89PNG")

    @pytest.mark.asyncio
    async def test_code_screenshot_keeps_code_beyond_the_output_limit(self) -> None:
        code = "\n".join(f"value_{i:03d} = {i}  # " + "x" * 70 for i in range(50))
        assert len(code) > 4000  # past the terminal-output char limit
        full = _image(await generate_code_screenshot(code))
        clipped = _image(await generate_terminal_screenshot(code))
        assert full.height > clipped.height


class TestScreenshotService:
    @pytest.mark.asyncio
    async def test_unsupported_results_get_no_screenshot(self) -> None:
        results = [TaskExecutionResult(task_id="t1", result=_result(ExecutionStatus.UNSUPPORTED, stderr="x"))]
        assert await ScreenshotService().capture_many(results) == {}

    @pytest.mark.asyncio
    async def test_success_failed_and_timeout_are_captured(self) -> None:
        results = [
            TaskExecutionResult(task_id="ok", result=_result(ExecutionStatus.SUCCESS, stdout="42")),
            TaskExecutionResult(task_id="bad", result=_result(ExecutionStatus.FAILED, stderr="Traceback")),
            TaskExecutionResult(task_id="slow", result=_result(ExecutionStatus.TIMEOUT, stderr="too slow")),
        ]
        shots = await ScreenshotService().capture_many(results)
        assert set(shots) == {"ok", "bad", "slow"}
        assert all(png.startswith(b"\x89PNG") for png in shots.values())

    @pytest.mark.asyncio
    async def test_silent_success_still_gets_a_placeholder_image(self) -> None:
        results = [TaskExecutionResult(task_id="t", result=_result(ExecutionStatus.SUCCESS, stdout=""))]
        shots = await ScreenshotService().capture_many(results)
        assert shots["t"].startswith(b"\x89PNG")
