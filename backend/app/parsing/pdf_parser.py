from io import BytesIO

import pdfplumber

from app.core.errors import AppError

# A long token (an identifier, a quoted attribute) broken mid-word by the
# table cell's width, e.g.  android:id="@+id/r  /  ootLayout"
_BROKEN_TOKEN_CHARS = "/@="


def _cell_text(value) -> str:
    """One cell -> one line. Wrapped lines are joined with a space, except when
    a quoted identifier was split mid-token (so `@+id/r` + `ootLayout` rejoins)."""
    if not value:
        return ""
    result = ""
    for line in (part.strip() for part in str(value).split("\n")):
        if not line:
            continue
        if not result:
            result = line
            continue
        last_token = result.rsplit(" ", 1)[-1]
        broken = last_token.count('"') % 2 == 1 and any(c in last_token for c in _BROKEN_TOKEN_CHARS)
        result += line if broken else " " + line
    return result


def _table_rows(raw_rows: list[list]) -> list[list[str]]:
    """Drops empty/merged cells, keeps order, pads short rows to the header width.

    Word tables with merged columns come back from pdfplumber with the header
    and the data on different column indexes plus lots of None cells; reading
    each row's non-empty cells left to right recovers the real columns.
    """
    rows = [[text for text in (_cell_text(c) for c in row) if text] for row in raw_rows]
    rows = [row for row in rows if row]
    if rows:
        width = len(rows[0])
        rows = [row + [""] * (width - len(row)) for row in rows]
    return rows


def _contains(outer, inner, tolerance: float = 1.0) -> bool:
    return (
        outer[0] - tolerance <= inner[0]
        and outer[1] - tolerance <= inner[1]
        and outer[2] + tolerance >= inner[2]
        and outer[3] + tolerance >= inner[3]
    )


def _accepted_tables(page) -> list[tuple[tuple, list[list[str]]]]:
    """Real tables only: >= 2 rows and >= 2 columns. Single-cell boxes (inline
    code highlights, callouts) and tables nested inside another are ignored so
    their text stays in the normal flow."""
    found = []
    for table in page.find_tables():
        rows = _table_rows(table.extract())
        if len(rows) >= 2 and len(rows[0]) >= 2:
            found.append((table.bbox, rows))
    kept = [
        item
        for item in found
        if not any(other is not item and _contains(other[0], item[0]) for other in found)
    ]
    return sorted(kept, key=lambda item: item[0][1])


def _segment_text(page, top: float, bottom: float) -> str:
    top, bottom = max(top, 0.0), min(bottom, float(page.height))
    if bottom - top < 1:
        return ""
    return (page.crop((0, top, page.width, bottom)).extract_text() or "").strip()


def _page_blocks(page) -> list[tuple[str, object]]:
    """The page as ordered ("text", str) / ("table", rows) blocks."""
    tables = _accepted_tables(page)
    if not tables:
        return [("text", (page.extract_text() or "").strip())]
    blocks: list[tuple[str, object]] = []
    cursor = 0.0
    for bbox, rows in tables:
        blocks.append(("text", _segment_text(page, cursor, bbox[1])))
        blocks.append(("table", rows))
        cursor = bbox[3]
    blocks.append(("text", _segment_text(page, cursor, float(page.height))))
    return [block for block in blocks if block[0] == "table" or block[1]]


def parse_pdf(content: bytes) -> str:
    """Extracts text from a PDF, in order, keeping tables as tables.

    Each table row becomes one line with cells separated by ' | ' (an empty
    cell, e.g. a column the student must fill in, leaves a trailing '|'), so
    the AI sees which value belongs to which column instead of word-wrapped
    cell lines interleaved. A header row repeated at the top of a continued
    table on the next page is dropped. Text inside images is not read.

    Scanned/image-only PDFs with no text layer are treated as unreadable
    rather than silently returning an empty report — that's a
    LAB_READ_FAILED case, not a success with nothing in it.
    """
    lines: list[str] = []
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            previous_header: list[str] | None = None  # set while a table ends a page
            for page in pdf.pages:
                try:
                    blocks = _page_blocks(page)
                except Exception:  # noqa: BLE001 - never lose a page over table handling
                    blocks = [("text", (page.extract_text() or "").strip())]

                for index, (kind, value) in enumerate(blocks):
                    if kind == "text":
                        lines.append(str(value))
                        previous_header = None
                        continue
                    rows = list(value)  # type: ignore[arg-type]
                    if index == 0 and previous_header is not None and rows[0] == previous_header:
                        rows = rows[1:]  # continuation page repeating the header
                    for row in rows:
                        lines.append(" | ".join(row).rstrip())
                    previous_header = None
                if blocks and blocks[-1][0] == "table":
                    previous_header = list(blocks[-1][1])[0]  # type: ignore[index]
                else:
                    previous_header = None
    except Exception as exc:
        raise AppError("LAB_READ_FAILED", "Could not read the PDF file.") from exc

    text = "\n".join(lines).strip()
    if not text:
        raise AppError(
            "LAB_READ_FAILED",
            "No readable text was found in this PDF. If it's a scanned "
            "document, please upload a text-based PDF, DOC, or DOCX instead.",
        )
    return text
