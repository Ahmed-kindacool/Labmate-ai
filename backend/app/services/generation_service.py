from app.parsing import parse_lab
from app.schemas.generate import GenerateSuccessResponse
from app.schemas.student import StudentInfo


class GenerationService:
    """Coordinates the full generation pipeline:
        Lab Parser -> AI Service -> Code Executor -> Screenshot Service
        -> Template Service -> DOCX Generator

    Ported from `GenerationService` in
    src/lib/generation/generation.service.ts. Per the original Phase 1
    scope, this intentionally returns a mock response so the frontend can be
    built against a stable API contract before the real pipeline stages
    exist. Each stage gets wired in during its phase.
    """

    async def generate(
        self,
        student: StudentInfo,
        lab_filename: str,
        lab_content_type: str,
        lab_bytes: bytes,
    ) -> GenerateSuccessResponse:
        # Referenced so linters don't flag unused params until later stages
        # (AI, execution, templates) consume them.
        _ = student

        # Phase 2: parse the lab into normalized text. A read failure here
        # raises AppError("LAB_READ_FAILED", ...), which the route's
        # exception handler turns into a 400 response.
        parsed_lab = parse_lab(lab_bytes, lab_content_type, lab_filename)
        _ = parsed_lab  # consumed by Phase 3 (AI Service) once it exists

        # TODO(Phase 3): generated_lab = await ai_service.generate_solutions(parsed_lab)
        # TODO(Phase 4): execution_results = await code_executor.run(generated_lab)
        # TODO(Phase 5): screenshots = await screenshot_service.capture(execution_results)
        # TODO(Phase 6/7): docx = await docx_generator.render(template, ...)

        return GenerateSuccessResponse(download_url="/mock/sample-report.docx")
