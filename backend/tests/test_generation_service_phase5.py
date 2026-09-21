import pytest

from app.ai.service import AIService
from app.schemas.generate import TaskExecutionResult
from app.schemas.lab import ExecutionResult, ExecutionStatus
from app.schemas.student import StudentInfo
from app.services.generation_service import GenerationService
from tests.ai_fakes import FakeAIProvider


class _BoomScreenshotService:
    """Simulates Playwright/Chromium being broken/unavailable."""

    async def capture_many(self, execution_results: list[TaskExecutionResult]) -> dict[str, bytes]:
        raise RuntimeError("Chromium executable not found")


class _FixedScreenshotService:
    async def capture_many(self, execution_results: list[TaskExecutionResult]) -> dict[str, bytes]:
        return {r.task_id: b"\x89PNG-fake" for r in execution_results}


STUDENT = StudentInfo(
    name="Mahd",
    roll_number="1",
    university="air",
    class_section="x",
    instructor_name="x",
    course="x",
)


class TestGenerationServiceScreenshots:
    @pytest.mark.asyncio
    async def test_screenshot_failure_does_not_break_the_response(
        self, sample_pdf_bytes: bytes, sample_generated_lab
    ) -> None:
        service = GenerationService(
            ai_service=AIService(provider=FakeAIProvider(result=sample_generated_lab)),
            screenshot_service=_BoomScreenshotService(),
        )

        response = await service.generate(
            student=STUDENT,
            lab_filename="lab.pdf",
            lab_content_type="application/pdf",
            lab_bytes=sample_pdf_bytes,
        )

        assert response.status == "success"
        assert response.generated_lab is not None  # rest of the pipeline unaffected
        assert response.screenshots is None

    @pytest.mark.asyncio
    async def test_successful_screenshots_are_base64_encoded(
        self, sample_pdf_bytes: bytes, sample_generated_lab
    ) -> None:
        service = GenerationService(
            ai_service=AIService(provider=FakeAIProvider(result=sample_generated_lab)),
            screenshot_service=_FixedScreenshotService(),
        )

        response = await service.generate(
            student=STUDENT,
            lab_filename="lab.pdf",
            lab_content_type="application/pdf",
            lab_bytes=sample_pdf_bytes,
        )

        assert response.screenshots is not None
        assert "task-1" in response.screenshots
        import base64

        assert base64.b64decode(response.screenshots["task-1"]) == b"\x89PNG-fake"

    @pytest.mark.asyncio
    async def test_no_execution_results_means_no_screenshot_attempt(
        self, sample_pdf_bytes: bytes
    ) -> None:
        from app.schemas.lab import GeneratedLab

        lab_with_no_code = GeneratedLab(
            lab_title="No code lab",
            objectives=["Conceptual only"],
            tasks=[],
            conclusion="Done.",
        )
        service = GenerationService(
            ai_service=AIService(provider=FakeAIProvider(result=lab_with_no_code)),
            screenshot_service=_BoomScreenshotService(),  # would raise if ever called
        )

        response = await service.generate(
            student=STUDENT,
            lab_filename="lab.pdf",
            lab_content_type="application/pdf",
            lab_bytes=sample_pdf_bytes,
        )

        assert response.execution_results == []
        assert response.screenshots is None
