from io import BytesIO

from docx import Document

from app.core.errors import AppError


def parse_docx(content: bytes) -> str:
    """Extracts paragraph text from a .docx file, in document order.

    Tables aren't walked here — out of scope for Phase 2 (lab documents in
    this MVP are expected to be prose/task lists, not tabular). Revisit if
    real lab uploads turn out to rely on tables for task content.
    """
    try:
        document = Document(BytesIO(content))
    except Exception as exc:
        raise AppError("LAB_READ_FAILED", "Could not read the DOCX file.") from exc

    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs).strip()
    if not text:
        raise AppError("LAB_READ_FAILED", "The DOCX file appears to be empty.")
    return text
