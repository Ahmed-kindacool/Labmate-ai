from app.ai import AIService
from app.execution import get_executor
from app.parsing import parse_lab
from app.schemas.generate import GenerateSuccessResponse, TaskExecutionResult
from app.schemas.lab import GeneratedLab
from app.schemas.student import StudentInfo


class GenerationService:
    """Coordinates the full generation pipeline:
        Lab Parser -> AI Service -> Code Executor -> Screenshot Service
        -> Template Service -> DOCX Generator

    Ported from `GenerationService` in
    src/lib/generation/generation.service.ts. Per the original Phase 1
    scope, this intentionally returns a mock `download_url` so the frontend
    can be built against a stable API contract before the real DOCX
    pipeline exists (Phase 7). Each remaining stage gets wired in during
    its phase.
    """

    def __init__(self, ai_service: AIService | None = None) -> None:
        self._ai_service = ai_service or AIService()

    async def generate(
        self,
        student: StudentInfo,
        lab_filename: str,
        lab_content_type: str,
        lab_bytes: bytes,
    ) -> GenerateSuccessResponse:
        # Referenced so linters don't flag it as unused until templates
        # (Phase 6) need student-specific data.
        _ = student

        # Phase 2: parse the lab into normalized text. A read failure here
        # raises AppError("LAB_READ_FAILED", ...), which the route's
        # exception handler turns into a 400 response.
        parsed_lab = parse_lab(lab_bytes, lab_content_type, lab_filename)

        # Phase 3: generate structured solutions. A failure here raises
        # AppError("AI_GENERATION_FAILED", ...) -> 400 response.
        generated_lab = await self._ai_service.generate_solutions(parsed_lab)

        # Phase 4: execute any code the AI generated. Per-task failures
        # (a script that errors, times out, or is in an unsupported
        # language) are captured as ExecutionResult.status — they do NOT
        # raise or block the rest of the report, per the anti-fabrication
        # rule in AI_AND_GENERATION.md ("report the actual failure or omit
        # the screenshot", not fail the whole request).
        execution_results = await self._execute_tasks(generated_lab)

        # TODO(Phase 5): screenshots = await screenshot_service.capture(execution_results)
        # TODO(Phase 6/7): docx = await docx_generator.render(template, ...)

        return GenerateSuccessResponse(
            download_url="/mock/sample-report.docx",
            generated_lab=generated_lab,
            execution_results=execution_results,
        )

    async def _execute_tasks(self, generated_lab: GeneratedLab) -> list[TaskExecutionResult]:
        results: list[TaskExecutionResult] = []
        for task in generated_lab.tasks:
            if not task.code.strip():
                # A task the AI decided needed no code (per the prompt
                # rules in app/ai/prompts.py) — nothing to run.
                continue
            executor = get_executor(task.language)
            result = await executor.execute(task.code)
            results.append(TaskExecutionResult(task_id=task.id, result=result))
        return results
