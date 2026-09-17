from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_FIELDS = {
    "name": "Mahd",
    "roll_number": "01-123456-001",
    "university": "bahria",
    "class_section": "BSAI-4A",
    "instructor_name": "Dr. Example",
    "course": "Artificial Intelligence",
}


def test_generate_with_real_pdf_succeeds(sample_pdf_bytes: bytes) -> None:
    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("lab04.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_generate_with_real_docx_succeeds(sample_docx_bytes: bytes) -> None:
    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={
            "lab_file": (
                "lab03.docx",
                sample_docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_generate_with_unreadable_pdf_returns_lab_read_failed(empty_pdf_bytes: bytes) -> None:
    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("scan.pdf", empty_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "LAB_READ_FAILED"


def test_generate_with_missing_fields_returns_field_errors() -> None:
    response = client.post(
        "/api/v1/labs/generate",
        data={},
        files={"lab_file": ("lab.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_INPUT"
    assert "name" in body["field_errors"]


def test_generate_with_unsupported_file_type() -> None:
    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "UNSUPPORTED_FILE"


def test_generate_with_oversized_file_returns_file_too_large() -> None:
    big_content = b"%PDF-1.4" + b"0" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/labs/generate",
        data=VALID_FIELDS,
        files={"lab_file": ("big.pdf", big_content, "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "FILE_TOO_LARGE"
