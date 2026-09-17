import shutil

import pytest

from app.core.errors import AppError
from app.parsing.doc_parser import parse_doc
from app.parsing.docx_parser import parse_docx
from app.parsing.factory import parse_lab
from app.parsing.pdf_parser import parse_pdf


class TestParsePdf:
    def test_extracts_text(self, sample_pdf_bytes: bytes) -> None:
        text = parse_pdf(sample_pdf_bytes)
        assert "Constraint Satisfaction Problems" in text
        assert "N-Queens" in text

    def test_empty_pdf_raises_lab_read_failed(self, empty_pdf_bytes: bytes) -> None:
        with pytest.raises(AppError) as exc_info:
            parse_pdf(empty_pdf_bytes)
        assert exc_info.value.code == "LAB_READ_FAILED"

    def test_corrupt_pdf_raises_lab_read_failed(self) -> None:
        with pytest.raises(AppError) as exc_info:
            parse_pdf(b"this is not a pdf")
        assert exc_info.value.code == "LAB_READ_FAILED"


class TestParseDocx:
    def test_extracts_text(self, sample_docx_bytes: bytes) -> None:
        text = parse_docx(sample_docx_bytes)
        assert "Prolog Basics" in text
        assert "family relationships" in text

    def test_empty_docx_raises_lab_read_failed(self, empty_docx_bytes: bytes) -> None:
        with pytest.raises(AppError) as exc_info:
            parse_docx(empty_docx_bytes)
        assert exc_info.value.code == "LAB_READ_FAILED"

    def test_corrupt_docx_raises_lab_read_failed(self) -> None:
        with pytest.raises(AppError) as exc_info:
            parse_docx(b"this is not a docx")
        assert exc_info.value.code == "LAB_READ_FAILED"


class TestParseDoc:
    def test_missing_antiword_gives_actionable_message(self, monkeypatch) -> None:
        monkeypatch.setattr(shutil, "which", lambda _name: None)
        with pytest.raises(AppError) as exc_info:
            parse_doc(b"irrelevant")
        assert exc_info.value.code == "LAB_READ_FAILED"
        assert "docx or .pdf" in exc_info.value.message

    def test_corrupt_doc_raises_lab_read_failed(self) -> None:
        if shutil.which("antiword") is None:
            pytest.skip("antiword not installed in this environment")
        with pytest.raises(AppError) as exc_info:
            parse_doc(b"not a real doc file")
        assert exc_info.value.code == "LAB_READ_FAILED"


class TestParserFactory:
    def test_routes_pdf_to_pdf_parser(self, sample_pdf_bytes: bytes) -> None:
        parsed = parse_lab(sample_pdf_bytes, "application/pdf", "lab04.pdf")
        assert "Constraint Satisfaction" in parsed.raw_text
        assert parsed.tasks == []

    def test_routes_docx_to_docx_parser(self, sample_docx_bytes: bytes) -> None:
        parsed = parse_lab(
            sample_docx_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "lab03.docx",
        )
        assert "Prolog Basics" in parsed.raw_text

    def test_guesses_title_from_first_line(self, sample_pdf_bytes: bytes) -> None:
        parsed = parse_lab(sample_pdf_bytes, "application/pdf", "lab04.pdf")
        assert parsed.title == "Lab 04: Constraint Satisfaction Problems"

    def test_title_guess_skips_blank_leading_lines(self) -> None:
        from app.parsing.factory import _guess_title

        assert _guess_title("\n\n  \nActual Title\nmore text") == "Actual Title"

    def test_title_guess_returns_none_for_blank_text(self) -> None:
        from app.parsing.factory import _guess_title

        assert _guess_title("   \n\n  ") is None

    def test_unsupported_type_raises_unsupported_file(self) -> None:
        with pytest.raises(AppError) as exc_info:
            parse_lab(b"whatever", "text/plain", "notes.txt")
        assert exc_info.value.code == "UNSUPPORTED_FILE"
