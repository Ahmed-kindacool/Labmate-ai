"""Regression tests for the 'it doesn't actually generate reports' fixes."""

import io
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from docx import Document

from app.ai.openai_provider import OpenAIProvider, _parse_generated_lab
from app.core.config import Settings, settings
from app.core.errors import AppError
from app.documents import DocxGenerator
from app.domain.university import University
from app.schemas.lab import GeneratedLab, GeneratedTaskSolution, ParsedLab
from app.schemas.student import StudentInfo

_LAB = {
    "lab_title": "Lab 1",
    "objectives": ["Learn loops"],
    "tasks": [
        {
            "id": "task-1",
            "description": "Print numbers.",
            "language": "python",
            "filename": "a.py",
            "code": "print(1)",
            "explanation": "Prints one.",
        }
    ],
    "conclusion": "Loops are useful.",
}


def _client_returning(*contents):
    """Each call returns the next content (or raises it if it's an exception)."""
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        item = contents[min(len(calls), len(contents)) - 1]
        if isinstance(item, Exception):
            raise item
        message = MagicMock()
        message.content = item
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    client = MagicMock()
    client.chat.completions.create = create
    client.calls = calls
    return client


class _HttpError(Exception):
    def __init__(self, status_code):
        super().__init__(f"http {status_code}")
        self.status_code = status_code


@pytest.fixture
def parsed() -> ParsedLab:
    return ParsedLab(title="t", raw_text="Task 1: print", tasks=[])


class TestAiParsing:
    def test_code_fenced_json_is_accepted(self) -> None:
        lab = _parse_generated_lab("```json\n" + json.dumps(_LAB) + "\n```")
        assert lab.lab_title == "Lab 1"

    def test_prose_around_json_is_ignored(self) -> None:
        lab = _parse_generated_lab("Sure! Here you go:\n" + json.dumps(_LAB) + "\nHope that helps.")
        assert len(lab.tasks) == 1

    def test_missing_optional_fields_are_defaulted_not_fatal(self) -> None:
        sparse = {"lab_title": "L", "tasks": [{"description": "d", "language": "Python", "code": "print(1)"}]}
        lab = _parse_generated_lab(json.dumps(sparse))
        task = lab.tasks[0]
        assert task.id == "task-1"
        assert task.filename == "task1.py"
        assert task.language == "python"
        assert lab.objectives == [] and lab.conclusion == ""

    def test_no_code_task_keeps_empty_filename(self) -> None:
        lab = _parse_generated_lab(json.dumps({"lab_title": "L", "tasks": [{"description": "theory"}]}))
        assert lab.tasks[0].code == "" and lab.tasks[0].filename == ""

    @pytest.mark.parametrize("raw", ["", "no json here", '{"tasks": "nope"}', '{"unexpected": 1}'])
    def test_garbage_still_fails_cleanly(self, raw: str) -> None:
        with pytest.raises(AppError) as exc:
            _parse_generated_lab(raw)
        assert exc.value.code == "AI_GENERATION_FAILED"


class TestProviderBehaviour:
    @pytest.mark.asyncio
    async def test_retries_without_json_mode_when_provider_rejects_it(self, parsed) -> None:
        client = _client_returning(_HttpError(400), json.dumps(_LAB))
        lab = await OpenAIProvider(client=client, model="m").generate_solutions(parsed)
        assert lab.lab_title == "Lab 1"
        assert "response_format" in client.calls[0]
        assert "response_format" not in client.calls[1]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "fragment"),
        [(401, "API key"), (404, "model"), (429, "busy or out of quota")],
    )
    async def test_failures_give_actionable_messages(self, parsed, status, fragment) -> None:
        client = _client_returning(_HttpError(status))
        with pytest.raises(AppError) as exc:
            await OpenAIProvider(client=client, model="m").generate_solutions(parsed)
        assert fragment in exc.value.message

    @pytest.mark.asyncio
    async def test_missing_key_is_called_out_explicitly(self, parsed, monkeypatch) -> None:
        monkeypatch.setattr(settings, "ai_api_key", "")
        with pytest.raises(AppError) as exc:
            await OpenAIProvider().generate_solutions(parsed)
        assert "not configured" in exc.value.message


def _student() -> StudentInfo:
    return StudentInfo(
        name="Haziq",
        roll_number="242242",
        university=University.NUST,
        class_section="BSCS-3A",
        instructor_name="Dr. X",
        course="PF",
    )


def _all_text(docx_bytes: bytes) -> str:
    document = Document(io.BytesIO(docx_bytes))
    return "\n".join(
        "".join(t.text or "" for t in p.xpath(".//w:t")) for p in document.element.xpath(".//w:p")
    )


class TestReportContent:
    @pytest.mark.parametrize("university", [University.AIR, University.BAHRIA, University.NUST])
    def test_report_contains_objectives_explanation_conclusion_and_class_section(self, university) -> None:
        student = _student().model_copy(update={"university": university})
        lab = GeneratedLab.model_validate(_LAB)
        text = _all_text(DocxGenerator().generate(student, lab))

        assert "Objectives" in text and "Learn loops" in text
        assert "Explanation:" in text and "Prints one." in text
        assert "Conclusion" in text and "Loops are useful." in text
        assert "BSCS-3A" in text  # the form field used to be silently dropped
        assert "{{" not in text  # no unfilled placeholders left behind

    def test_empty_objectives_and_conclusion_add_no_empty_headings(self) -> None:
        lab = GeneratedLab(
            lab_title="L",
            objectives=[],
            tasks=[
                GeneratedTaskSolution(
                    id="t", description="d", language="", filename="", code="", explanation=""
                )
            ],
            conclusion="",
        )
        text = _all_text(DocxGenerator().generate(_student(), lab))
        assert "Objectives" not in text and "Conclusion" not in text and "Explanation:" not in text


class TestConfig:
    def test_cors_origins_accepts_a_comma_separated_list(self) -> None:
        cfg = Settings(frontend_origin="https://a.example/, http://localhost:5173 ,", _env_file=None)
        assert cfg.cors_origins == ["https://a.example", "http://localhost:5173"]


class TestStaticServing:
    def test_built_frontend_is_served_and_api_still_wins(self, tmp_path, monkeypatch) -> None:
        import importlib

        (tmp_path / "index.html").write_text("<html>SPA</html>")
        monkeypatch.setattr(settings, "frontend_dist_dir", str(tmp_path))
        import app.main as main_module

        reloaded = importlib.reload(main_module)
        try:
            from fastapi.testclient import TestClient

            client = TestClient(reloaded.app)
            assert "SPA" in client.get("/").text
            assert client.get("/api/v1/health").status_code == 200
        finally:
            monkeypatch.setattr(settings, "frontend_dist_dir", "")
            importlib.reload(main_module)
