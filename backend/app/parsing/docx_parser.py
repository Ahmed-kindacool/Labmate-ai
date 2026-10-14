from io import BytesIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.errors import AppError


def _table_lines(table: Table) -> list[str]:
    """One line per row, cells joined with ' | ' (merged cells de-duplicated)."""
    lines = []
    for row in table.rows:
        cells: list[str] = []
        for cell in row.cells:
            text = " ".join(cell.text.split())
            if text and (not cells or cells[-1] != text):
                cells.append(text)
        if cells:
            lines.append(" | ".join(cells))
    return lines


def parse_docx(content: bytes) -> str:
    """Extracts text from a .docx file in document order -- paragraphs AND tables.

    Lab manuals often put the real specification in a table (screen/layout
    maps, fill-in tables, marking schemes), so tables are included, one row
    per line with cells separated by ' | '. Text inside images is not read.
    """
    try:
        document = Document(BytesIO(content))
    except Exception as exc:
        raise AppError("LAB_READ_FAILED", "Could not read the DOCX file.") from exc

    lines: list[str] = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = Paragraph(child, document).text
            if text.strip():
                lines.append(text)
        elif tag == "tbl":
            lines.extend(_table_lines(Table(child, document)))

    text = "\n".join(lines).strip()
    if not text:
        raise AppError("LAB_READ_FAILED", "The DOCX file appears to be empty.")
    return text
