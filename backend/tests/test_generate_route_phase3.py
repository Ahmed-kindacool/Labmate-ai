from fastapi.testclient import TestClient

from app.ai.service import AIService
from app.main import app
from app.routes import lab as lab_route
from app.schemas.lab import GeneratedLab
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


def test_generate_returns_generated_lab_from_real_pdf(
    sample_pdf_bytes: bytes, sample_generated_lab: GeneratedLab, monkeypatch
) -> None:
    fake_provider = FakeAIProvider(result=sample_generated_lab)
    monkeypatch.setattr(
        lab_route, "generation_service", GenerationService(ai_service=AIService(provider=fake_provider))
    )

    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("lab04.pdf", sample_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["generated_lab"]["lab_title"] == sample_generated_lab.lab_title
    assert len(body["generated_lab"]["tasks"]) == 1

    # Confirms Phase 2's real parsed text actually reached the AI layer,
    # not just that the mock returned something.
    assert "Constraint Satisfaction" in fake_provider.received_parsed_lab.raw_text


def test_generate_surfaces_ai_failure_as_400(sample_pdf_bytes: bytes, monkeypatch) -> None:
    from app.core.errors import AppError

    fake_provider = FakeAIProvider(error=AppError("AI_GENERATION_FAILED", "The AI is down."))
    monkeypatch.setattr(
        lab_route, "generation_service", GenerationService(ai_service=AIService(provider=fake_provider))
    )

    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("lab04.pdf", sample_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "AI_GENERATION_FAILED"
