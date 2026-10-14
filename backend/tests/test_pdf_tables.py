"""PDF tables must reach the AI as rows of cells, not word-wrapped jumble."""

import io

import pytest
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.parsing.pdf_parser import _cell_text, parse_pdf

_STYLES = getSampleStyleSheet()
_GRID = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)])


def _pdf(flowables) -> bytes:
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4).build(flowables)
    return buffer.getvalue()


def _cell(text: str):
    return Paragraph(text, _STYLES["BodyText"])


class TestCellText:
    def test_wrapped_lines_are_joined_with_a_space(self) -> None:
        assert _cell_text("RelativeLayout, aligned\nto the parent top") == "RelativeLayout, aligned to the parent top"

    def test_identifier_split_mid_token_is_rejoined(self) -> None:
        assert _cell_text('RelativeLayout with\nandroid:id="@+id/r\nootLayout"') == 'RelativeLayout with android:id="@+id/rootLayout"'

    def test_an_opened_quote_in_normal_prose_does_not_glue_words(self) -> None:
        assert _cell_text('Show "Hello,\nyou are registered."') == 'Show "Hello, you are registered."'

    def test_empty_values(self) -> None:
        assert _cell_text(None) == "" and _cell_text("  \n ") == ""


class TestParsePdfTables:
    def test_table_rows_keep_their_columns_and_surrounding_text_stays_in_order(self) -> None:
        table = Table(
            [
                ["Screen area", "Layout to use", "Lab"],
                [_cell("Root of the screen"), _cell("RelativeLayout with an id"), "03, 04"],
                [_cell("Header (top)"), _cell("RelativeLayout, aligned to the parent top"), "03, 04"],
            ],
            colWidths=[120, 250, 60],
        )
        table.setStyle(_GRID)
        text = parse_pdf(_pdf([Paragraph("Intro line.", _STYLES["Normal"]), Spacer(1, 12), table, Spacer(1, 12), Paragraph("Outro line.", _STYLES["Normal"])]))
        lines = text.splitlines()
        assert lines[0] == "Intro line."
        assert "Screen area | Layout to use | Lab" in lines
        assert "Root of the screen | RelativeLayout with an id | 03, 04" in lines
        assert "Header (top) | RelativeLayout, aligned to the parent top | 03, 04" in lines
        assert lines[-1] == "Outro line."
        assert lines.index("Screen area | Layout to use | Lab") < lines.index("Outro line.")

    def test_blank_fill_in_column_leaves_a_trailing_pipe(self) -> None:
        table = Table([["Action", "Callbacks observed"], ["App opened", ""], ["Home pressed", ""]], colWidths=[200, 200])
        table.setStyle(_GRID)
        text = parse_pdf(_pdf([table]))
        assert "Action | Callbacks observed" in text
        assert "App opened |" in text.splitlines()
        assert "Home pressed |" in text.splitlines()

    def test_header_repeated_on_a_continued_page_is_dropped(self) -> None:
        rows = [["Criteria", "Marks"]] + [[f"Item {i}", str(i)] for i in range(1, 80)]
        table = Table(rows, colWidths=[300, 80], repeatRows=1)
        table.setStyle(_GRID)
        text = parse_pdf(_pdf([table]))
        assert text.count("Criteria | Marks") == 1
        assert "Item 1 | 1" in text and "Item 79 | 79" in text

    def test_single_cell_boxes_are_not_treated_as_tables(self) -> None:
        box = Table([["ivProfile"], ["tvWelcome"]], colWidths=[100])
        box.setStyle(_GRID)
        text = parse_pdf(_pdf([Paragraph("Views:", _STYLES["Normal"]), box]))
        assert "ivProfile" in text and "tvWelcome" in text
        assert "|" not in text

    def test_pdf_without_tables_is_unchanged_plain_text(self) -> None:
        text = parse_pdf(_pdf([Paragraph("Just a paragraph of lab text.", _STYLES["Normal"])]))
        assert text == "Just a paragraph of lab text."

    def test_unreadable_pdf_still_raises(self) -> None:
        from app.core.errors import AppError

        with pytest.raises(AppError):
            parse_pdf(b"not a pdf")
