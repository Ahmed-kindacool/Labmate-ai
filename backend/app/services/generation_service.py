import asyncio
import base64

from app.ai import AIService
from app.documents import DocxGenerator
from app.execution import get_executor
from app.parsing import parse_lab
from app.schemas.generate import GenerateSuccessResponse, TaskExecutionResult
from app.schemas.lab import GeneratedLab
from app.schemas.student import StudentInfo
from app.screenshots import ScreenshotService, generate_code_screenshot
from app.execution import is_runnable_language
from app.screenshots.image_renderer import CODE_SCREENSHOT_MAX_LINES

_MAX_PARALLEL_EXECUTIONS = 3
_DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class GenerationService:
    """Coordinates the full generation pipeline:
        Lab Parser -> AI Service -> Code Executor -> Screenshot Service
        -> Template Registry -> DOCX Generator

    Ported from `GenerationService` in
    src/lib/generation/generation.service.ts. As of Phase 7, every stage
    is real -- this no longer returns a mock `download_url`.
    """

    def __init__(
        self,
        ai_service: AIService | None = None,
        screenshot_service: ScreenshotService | None = None,
        docx_generator: DocxGenerator | None = None,
    ) -> None:
        self._ai_service = ai_service or AIService()
        self._screenshot_service = screenshot_service or ScreenshotService()
        self._docx_generator = docx_generator or DocxGenerator()

    async def generate(
        self,
        student: StudentInfo,
        lab_filename: str,
        lab_content_type: str,
        lab_bytes: bytes,
    ) -> GenerateSuccessResponse:
        # Phase 2: parse the lab into normalized text. A read failure here
        # raises AppError("LAB_READ_FAILED", ...), which the route's
        # exception handler turns into a 400 response.
        parsed_lab = parse_lab(lab_bytes, lab_content_type, lab_filename)

        # Phase 3: generate structured solutions. A failure here raises
        # AppError("AI_GENERATION_FAILED", ...) -> 400 response.
        generated_lab = await self._ai_service.generate_solutions(parsed_lab)

        # Phase 4: execute any code the AI generated. Per-task failures
        # (a script that errors, times out, or is in an unsupported
        # language) are captured as ExecutionResult.status -- they do NOT
        # raise or block the rest of the report, per the anti-fabrication
        # rule in AI_AND_GENERATION.md ("report the actual failure or omit
        # the screenshot", not fail the whole request).
        execution_results = await self._execute_tasks(generated_lab)

        # Phase 5: screenshot real output (success or a genuine failure).
        # A screenshotting problem (e.g. Playwright/Chromium unavailable)
        # shouldn't take down report generation either -- the report is
        # still useful without images, so this degrades to "no
        # screenshots" rather than raising.
        screenshots = await self._capture_screenshots(execution_results)

        code_screenshots = await self._capture_code_screenshots(generated_lab)

        lab_metadata = {}

        # Phase 6/7: render the final report. DocxGenerator (which calls
        # TemplateRegistry itself) raises AppError("REPORT_GENERATION_FAILED",
        # ...) on failure, same convention as every stage above -- the
        # route's existing exception handler already covers this without
        # any new wiring. python-docx is synchronous/CPU-bound, so this
        # runs off the event loop rather than blocking it.
        docx_bytes = await asyncio.to_thread(
            self._docx_generator.generate,
            student,
            generated_lab,
            execution_results,
            screenshots,
            code_screenshots,
            lab_metadata,
        )

        # See docs/DOCX_GENERATION.md "Why download_url is a data URI" --
        # resolves the "Open question" in docs/API_CONTRACT.md without a
        # new endpoint or any server-side file storage.
        download_url = _to_data_uri(docx_bytes)

        return GenerateSuccessResponse(
            download_url=download_url,
            generated_lab=generated_lab,
            execution_results=execution_results,
            screenshots=screenshots,
        )

    async def _execute_tasks(self, generated_lab: GeneratedLab) -> list[TaskExecutionResult]:
        # A task with no code (conceptual / written answer) has nothing to run.
        runnable = [task for task in generated_lab.tasks if task.code.strip()]
        # A few at a time: much faster than one-by-one for a big lab, while
        # still bounding how many sandboxed processes run concurrently.
        semaphore = asyncio.Semaphore(_MAX_PARALLEL_EXECUTIONS)

        async def run(task) -> TaskExecutionResult:
            async with semaphore:
                result = await get_executor(task.language).execute(task.code)
            return TaskExecutionResult(task_id=task.id, result=result)

        return list(await asyncio.gather(*(run(task) for task in runnable)))

    async def _capture_code_screenshots(self, generated_lab: GeneratedLab) -> dict[str, str]:
        screenshots: dict[str, str] = {}
        for task in generated_lab.tasks:
            if not task.code.strip():
                continue
            if generated_lab.code_as_text or not is_runnable_language(task.language):
                continue  # shown as real text, never as a picture of code
            if len(task.code.splitlines()) > CODE_SCREENSHOT_MAX_LINES:
                continue  # too tall for a page; the DOCX uses a text block instead
            try:
                png = await generate_code_screenshot(task.code)
            except Exception:
                # The DOCX falls back to a text code block for this task.
                continue
            screenshots[task.id] = base64.b64encode(png).decode("ascii")
        return screenshots

    async def _capture_screenshots(
        self, execution_results: list[TaskExecutionResult]
    ) -> dict[str, str] | None:
        if not execution_results:
            return None
        try:
            screenshots = await self._screenshot_service.capture_many(execution_results)
        except Exception:
            # Screenshotting is enhancement, not core correctness -- a
            # missing/broken Chromium install shouldn't block a report
            # that already has real generated code and execution output.
            return None
        if not screenshots:
            return None
        return {task_id: base64.b64encode(png).decode("ascii") for task_id, png in screenshots.items()}


def _to_data_uri(docx_bytes: bytes) -> str:
    encoded = base64.b64encode(docx_bytes).decode("ascii")
    return f"data:{_DOCX_MIME_TYPE};base64,{encoded}"
