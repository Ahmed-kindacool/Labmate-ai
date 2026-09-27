from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.generate import TaskExecutionResult
from app.schemas.lab import ExecutionResult, ExecutionStatus
from app.screenshots import generate_terminal_screenshot
from app.screenshots.service import ScreenshotService
from app.screenshots.terminal_renderer import render_terminal_html


class TestRenderTerminalHtml:
    def test_escapes_html_in_output(self) -> None:
        html_out = render_terminal_html("<script>alert(1)</script>")
        assert "<script>alert(1)</script>" not in html_out
        assert "&lt;script&gt;" in html_out

    def test_truncates_long_output(self) -> None:
        html_out = render_terminal_html("x" * 3000)
        assert "...[Output Truncated]" in html_out
        assert "x" * 2000 in html_out
        assert "x" * 2001 not in html_out

    def test_short_output_not_truncated(self) -> None:
        html_out = render_terminal_html("hello world")
        assert "hello world" in html_out
        assert "Truncated" not in html_out


def _make_mock_browser() -> MagicMock:
    page = MagicMock()
    page.set_content = AsyncMock()
    locator = MagicMock()
    locator.screenshot = AsyncMock(return_value=b"fake-png-bytes")
    page.locator = MagicMock(return_value=locator)

    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()
    return browser


class TestScreenshotService:
    @pytest.mark.asyncio
    async def test_no_capturable_results_skips_browser_entirely(self) -> None:
        results = [
            TaskExecutionResult(
                task_id="t1",
                result=ExecutionResult(status=ExecutionStatus.UNSUPPORTED, stdout="", stderr="x"),
            )
        ]
        service = ScreenshotService()

        with patch("app.screenshots.service.async_playwright") as mock_pw:
            screenshots = await service.capture_many(results)

        assert screenshots == {}
        mock_pw.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_result_uses_stdout(self) -> None:
        browser = _make_mock_browser()
        mock_playwright_ctx = MagicMock()
        mock_playwright_ctx.chromium.launch = AsyncMock(return_value=browser)
        mock_pw_cm = MagicMock()
        mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_playwright_ctx)
        mock_pw_cm.__aexit__ = AsyncMock(return_value=False)

        results = [
            TaskExecutionResult(
                task_id="t1",
                result=ExecutionResult(
                    status=ExecutionStatus.SUCCESS, stdout="hi there", stderr="", exit_code=0
                ),
            )
        ]
        service = ScreenshotService()

        with patch("app.screenshots.service.async_playwright", return_value=mock_pw_cm):
            screenshots = await service.capture_many(results)

        assert screenshots == {"t1": b"fake-png-bytes"}
        browser.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_result_uses_stderr_not_stdout(self) -> None:
        browser = _make_mock_browser()
        mock_playwright_ctx = MagicMock()
        mock_playwright_ctx.chromium.launch = AsyncMock(return_value=browser)
        mock_pw_cm = MagicMock()
        mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_playwright_ctx)
        mock_pw_cm.__aexit__ = AsyncMock(return_value=False)

        results = [
            TaskExecutionResult(
                task_id="t1",
                result=ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    stdout="",
                    stderr="Traceback: boom",
                    exit_code=1,
                ),
            )
        ]
        service = ScreenshotService()

        captured_html = {}

        async def fake_set_content(html_content: str) -> None:
            captured_html["value"] = html_content

        page = await browser.new_context()
        page_obj = await page.new_page()
        page_obj.set_content = fake_set_content

        with patch("app.screenshots.service.async_playwright", return_value=mock_pw_cm):
            await service.capture_many(results)

        assert "Traceback: boom" in captured_html["value"]

    @pytest.mark.asyncio
    async def test_reuses_one_browser_across_multiple_tasks(self) -> None:
        browser = _make_mock_browser()
        mock_playwright_ctx = MagicMock()
        mock_playwright_ctx.chromium.launch = AsyncMock(return_value=browser)
        mock_pw_cm = MagicMock()
        mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_playwright_ctx)
        mock_pw_cm.__aexit__ = AsyncMock(return_value=False)

        results = [
            TaskExecutionResult(
                task_id=f"t{i}",
                result=ExecutionResult(status=ExecutionStatus.SUCCESS, stdout=f"out {i}", stderr=""),
            )
            for i in range(3)
        ]
        service = ScreenshotService()

        with patch("app.screenshots.service.async_playwright", return_value=mock_pw_cm):
            screenshots = await service.capture_many(results)

        assert len(screenshots) == 3
        # One launch total, regardless of task count.
        mock_playwright_ctx.chromium.launch.assert_awaited_once()
        assert browser.new_context.await_count == 3


class TestWithRealUnmockedChromium:
    """Every test above mocks Playwright entirely -- reasonable given this
    project's sandboxes usually can't reach Playwright's CDN to download a
    browser (docs/Screenshots.md's original "known limitation"), but it
    means the actual screenshot-taking code has never been exercised for
    real. The `real_chromium_playwright` fixture (tests/conftest.py) makes
    that possible wherever a real Chromium happens to be available,
    without touching any production code -- see docs/PHASE9_TESTING.md.
    """

    @pytest.mark.asyncio
    async def test_generate_terminal_screenshot_produces_a_real_png(
        self, real_chromium_playwright
    ) -> None:
        result_bytes = await generate_terminal_screenshot("hello from a real browser")
        assert result_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # real PNG file signature
        assert len(result_bytes) > 100  # not a truncated/empty capture

    @pytest.mark.asyncio
    async def test_screenshot_service_produces_a_real_png_for_a_successful_task(
        self, real_chromium_playwright
    ) -> None:
        results = [
            TaskExecutionResult(
                task_id="t1",
                result=ExecutionResult(status=ExecutionStatus.SUCCESS, stdout="42", stderr=""),
            )
        ]
        service = ScreenshotService()

        screenshots = await service.capture_many(results)

        assert set(screenshots) == {"t1"}
        assert screenshots["t1"][:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_screenshot_service_real_multi_task_reuses_one_browser(
        self, real_chromium_playwright
    ) -> None:
        results = [
            TaskExecutionResult(
                task_id=f"t{i}",
                result=ExecutionResult(status=ExecutionStatus.SUCCESS, stdout=f"out {i}", stderr=""),
            )
            for i in range(3)
        ]
        service = ScreenshotService()

        screenshots = await service.capture_many(results)

        assert set(screenshots) == {"t0", "t1", "t2"}
        for png_bytes in screenshots.values():
            assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        # Genuinely different output text should not render to byte-identical
        # images -- a real sanity check only possible with a real browser.
        assert len({screenshots["t0"], screenshots["t1"], screenshots["t2"]}) == 3

    @pytest.mark.asyncio
    async def test_screenshot_service_real_failed_task_captures_real_stderr_text(
        self, real_chromium_playwright
    ) -> None:
        results = [
            TaskExecutionResult(
                task_id="t1",
                result=ExecutionResult(
                    status=ExecutionStatus.FAILED, stdout="", stderr="ZeroDivisionError: boom"
                ),
            )
        ]
        service = ScreenshotService()

        screenshots = await service.capture_many(results)

        # Can't OCR the PNG in a unit test, but a failed task's real error
        # text should still produce a distinctly-sized real image, not an
        # empty/blank one silently substituted for missing stdout.
        assert screenshots["t1"][:8] == b"\x89PNG\r\n\x1a\n"
        assert len(screenshots["t1"]) > 100
