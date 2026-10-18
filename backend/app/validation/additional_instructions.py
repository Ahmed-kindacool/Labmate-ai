"""The optional free-text "anything else you want in the report?" field."""

from app.core.errors import AppError

MAX_ADDITIONAL_INSTRUCTIONS_CHARS = 2000


def clean_additional_instructions(raw: str | None) -> str:
    """Normalizes the field; returns "" when nothing useful was sent.

    * strips control characters (keeps newlines and tabs) and surrounding space
    * rejects text longer than MAX_ADDITIONAL_INSTRUCTIONS_CHARS with a
      field-level error, so the UI can highlight the box
    """
    if not raw:
        return ""
    text = "".join(ch for ch in raw if ch in "\n\t" or ch.isprintable()).strip()
    if len(text) > MAX_ADDITIONAL_INSTRUCTIONS_CHARS:
        raise AppError(
            "INVALID_INPUT",
            "Please fix the highlighted fields.",
            {
                "additional_instructions": [
                    f"Too long: {len(text)} characters (maximum {MAX_ADDITIONAL_INSTRUCTIONS_CHARS})."
                ]
            },
        )
    return text
