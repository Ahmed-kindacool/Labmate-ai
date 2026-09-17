from app.core.errors import AppError
from app.parsing.doc_parser import parse_doc
from app.parsing.docx_parser import parse_docx
from app.parsing.pdf_parser import parse_pdf
from app.schemas.lab import ParsedLab

_PARSERS = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "application/msword": parse_doc,
}

_TITLE_MAX_LENGTH = 120


def parse_lab(content: bytes, content_type: str, filename: str) -> ParsedLab:
    """Converts an uploaded lab file into normalized text.

    This is the "Document Parser" stage in AI_AND_GENERATION.md's pipeline:
    Uploaded Lab -> Document Parser -> Normalized Lab Text. Identifying
    tasks from that text is the *next* stage (AI Lab Analysis, Phase 3) —
    `tasks` is intentionally left empty here rather than guessed at with
    regex heuristics that the AI step would just have to redo anyway.
    """
    parser = _PARSERS.get(content_type)
    if parser is None:
        # Should already be caught by validate_lab_file before this is called,
        # but guarded here too since this function may get called directly.
        raise AppError(
            "UNSUPPORTED_FILE",
            "Unsupported file type. Please upload a PDF, DOC, or DOCX file.",
        )

    raw_text = parser(content)
    title = _guess_title(raw_text) or filename

    return ParsedLab(title=title, raw_text=raw_text, tasks=[])


def _guess_title(raw_text: str) -> str | None:
    """Best-effort title guess: the first non-blank line, trimmed to a
    reasonable length. Just a UI/report label — not load-bearing for AI
    analysis, so no need for anything smarter here.
    """
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:_TITLE_MAX_LENGTH]
    return None
