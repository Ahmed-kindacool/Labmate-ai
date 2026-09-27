"""Phase 9: closes real coverage gaps found via `pytest --cov` that
weren't hit by any existing test -- not just low-value line-filling, but
genuinely untested behavior in security- and validation-relevant code
(app/core/errors.py's "never leak stack traces" promise, PROJECT_SPEC.md
§7; the blank-vs-whitespace-only field validator; the missing-file and
health-check paths; GenerationService skipping codeless tasks).
"""

from fastapi.testclient import TestClient

from app.ai.service import AIService
from app.core.errors import AppError
from app.main import app
from app.routes import lab as lab_route
from app.schemas.lab import GeneratedLab, GeneratedTaskSolution
from app.services.generation_service import GenerationService
from tests.ai_fakes import FakeAIProvider

client = TestClient(app)

VALID_FIELDS = {
    "name": "Mahd",
    "roll_number": "01-123456-001",
    "university": "bahria",
    "class_section": "BSAI-4A",
    "instructor_name": "Dr. Example",
    "course": "Artificial Intelligence",
}


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_whitespace_only_field_is_rejected_same_as_truly_empty(sample_pdf_bytes: bytes) -> None:
    # Distinct from an empty string: "   " passes a naive `if not value`
    # check but must still fail Zod's original `.trim().min(1)` behavior,
    # which `not_blank` (app/schemas/student.py) is a direct port of.
    fields = {**VALID_FIELDS, "name": "   "}

    response = client.post(
        "/api/v1/labs/generate",
        data=fields,
        files={"lab_file": ("lab.pdf", sample_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert "name" in body["field_errors"]


def test_missing_lab_file_field_entirely_returns_invalid_input() -> None:
    # Different from an unsupported/oversized/unreadable file -- this is
    # the multipart request omitting the "lab_file" field altogether.
    response = client.post("/api/v1/labs/generate", data=VALID_FIELDS)

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert "lab file" in body["message"].lower()


def test_unhandled_exception_returns_generic_500_without_leaking_details(
    sample_pdf_bytes: bytes, monkeypatch
) -> None:
    # A plain, un-wrapped exception -- not an AppError -- from anywhere in
    # the pipeline. app/core/errors.py's unhandled_error_handler must catch
    # ANY exception type, not just ones the app itself raises deliberately,
    # and must never surface the real exception message (which could
    # contain internal details) to the client.
    #
    # Starlette's TestClient defaults to `raise_server_exceptions=True`,
    # which re-raises into the test instead of invoking the registered
    # catch-all `Exception` handler -- deliberately, so test authors see
    # real tracebacks for genuine bugs. A real deployed server (uvicorn)
    # doesn't have this bypass; `raise_server_exceptions=False` here
    # exercises the actual production code path instead of the
    # test-debugging shortcut.
    non_raising_client = TestClient(app, raise_server_exceptions=False)
    fake_provider = FakeAIProvider(error=RuntimeError("Internal secret: db password is hunter2"))
    monkeypatch.setattr(
        lab_route,
        "generation_service",
        GenerationService(ai_service=AIService(provider=fake_provider)),
    )

    response = non_raising_client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("lab.pdf", sample_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "error"
    assert "hunter2" not in body["message"]
    assert "RuntimeError" not in body["message"]
    assert body["message"] == "Something went wrong. Please try again."


class TestGenerationServiceSkipsCodelessTasks:
    async def test_a_task_with_blank_code_is_never_sent_to_the_executor(self) -> None:
        lab = GeneratedLab(
            lab_title="Lab",
            objectives=[],
            tasks=[
                GeneratedTaskSolution(
                    id="task-1",
                    description="Conceptual question, no code needed.",
                    language="text",
                    filename="answer.txt",
                    code="",
                    explanation="N/A",
                ),
                GeneratedTaskSolution(
                    id="task-2",
                    description="Print a value.",
                    language="python",
                    filename="print.py",
                    code="print(1)",
                    explanation="Basic print.",
                ),
            ],
            conclusion="",
        )
        service = GenerationService()

        results = await service._execute_tasks(lab)

        result_task_ids = {r.task_id for r in results}
        assert result_task_ids == {"task-2"}
