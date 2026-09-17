from io import BytesIO

import pdfplumber

from app.core.errors import AppError


def parse_pdf(content: bytes) -> str:
    """Extracts text from a PDF's pages, in order.

    Scanned/image-only PDFs with no text layer are treated as unreadable
    rather than silently returning an empty report — that's a
    LAB_READ_FAILED case, not a success with nothing in it.
    """
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise AppError("LAB_READ_FAILED", "Could not read the PDF file.") from exc

    text = "\n".join(pages_text).strip()
    if not text:
        raise AppError(
            "LAB_READ_FAILED",
            "No readable text was found in this PDF. If it's a scanned "
            "document, please upload a text-based PDF, DOC, or DOCX instead.",
        )
    return text
