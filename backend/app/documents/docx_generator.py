import base64
import binascii
import io
import datetime
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.image.exceptions import UnrecognizedImageError
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from app.core.errors import AppError
from app.documents.docx_helpers import (
    find_placeholder_paragraph,
    insert_paragraph_after,
    iter_all_paragraphs,
    remove_paragraph,
    replace_placeholder_text,
)
from app.execution import is_runnable_language
from app.schemas.lab import ExecutionResult, ExecutionStatus, GeneratedLab, LabTable
from app.schemas.student import StudentInfo
from app.schemas.generate import TaskExecutionResult
from app.templates_registry import TemplateRegistry

_CODE_FONT = "Consolas"
_CODE_SIZE = Pt(9)
_SCREENSHOT_WIDTH = Inches(6.0)

_TEXT_FALLBACK_STATUSES = {ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT}

class DocxGenerator:
    """Fills a university's template.docx with a sequentially built lab report."""

    def __init__(self, template_registry: TemplateRegistry | None = None) -> None:
        self._templates = template_registry or TemplateRegistry()

    def generate(
        self,
        student: StudentInfo,
        generated_lab: GeneratedLab,
        execution_results: list[TaskExecutionResult] | None = None,
        screenshots: dict[str, str] | None = None,
        code_screenshots: dict[str, str] | None = None,
        lab_metadata: dict | None = None,
    ) -> bytes:
        
        execution_results = execution_results or []
        screenshots = screenshots or {}
        code_screenshots = code_screenshots or {}
        lab_metadata = lab_metadata or {}
        results_by_task = {r.task_id: r.result for r in execution_results}

        template_config = self._templates.get_template(student.university)
        
        try:
            document = Document(str(template_config.template_path))
        except Exception as exc:
            raise AppError("REPORT_GENERATION_FAILED", "Could not open the report template.") from exc

        self._replace_all_placeholders(document, student, generated_lab, lab_metadata)
        self._build_sequential_content(document, generated_lab, results_by_task, screenshots, code_screenshots)

        buffer = io.BytesIO()
        try:
            document.save(buffer)
        except Exception as exc:
            raise AppError("REPORT_GENERATION_FAILED", "Could not assemble final document.") from exc
        
        return buffer.getvalue()

    def _replace_all_placeholders(self, document: Document, student: StudentInfo, generated_lab: GeneratedLab, lab_metadata: dict) -> None:
        """Finds and replaces tags using a deep XML scanner to bypass MS Word Text Box limitations."""
        values = {
            "{{STUDENT_NAME}}": student.name,
            "{{CMS_ID}}": student.roll_number,
            "{{CLASS_SECTION}}": student.class_section,
            "{{INSTRUCTOR_NAME}}": student.instructor_name,
            "{{COURSE}}": student.course,
            "{{DEPARTMENT_TITLE}}": lab_metadata.get("department", "Department of Computing"),
            "{{LAB_TITLE}}": generated_lab.lab_title,
            "{{DATE}}": datetime.date.today().strftime('%B %d, %Y')
        }
        
        def aggressive_replace(paragraph):
            for token, value in values.items():
                replace_placeholder_text(paragraph, token, str(value))
                if token in paragraph.text:
                    paragraph.text = paragraph.text.replace(token, str(value))

        # "God-mode" XML Scanner: Hunts down every paragraph node anywhere in the document tree
        for p_node in document._element.xpath('.//w:p'):
            aggressive_replace(Paragraph(p_node, document))
            
        for section in document.sections:
            if section.header is not None and section.header._element is not None:
                for p_node in section.header._element.xpath('.//w:p'):
                    aggressive_replace(Paragraph(p_node, document))
            if section.footer is not None and section.footer._element is not None:
                for p_node in section.footer._element.xpath('.//w:p'):
                    aggressive_replace(Paragraph(p_node, document))

    def _build_sequential_content(self, document: Document, generated_lab: GeneratedLab, results_by_task: dict, screenshots: dict, code_screenshots: dict) -> None:
        target = find_placeholder_paragraph(document, "{{LAB_CONTENT}}")
        if target is None:
            return

        tasks = generated_lab.tasks
        anchor = target

        if generated_lab.objectives:
            anchor = insert_paragraph_after(anchor)
            self._heading_run(anchor, "Objectives")
            for objective in generated_lab.objectives:
                anchor = insert_paragraph_after(anchor)
                anchor.add_run(f"\u2022 {objective}")
            anchor = insert_paragraph_after(anchor)

        if generated_lab.steps:
            anchor = self._write_steps(anchor, generated_lab.steps)

        for index, task in enumerate(tasks, start=1):
            has_code = bool(task.code.strip())
            runnable = has_code and is_runnable_language(task.language)
            as_text = generated_lab.code_as_text or not runnable

            anchor = insert_paragraph_after(anchor)
            title = f"Task {index}: {task.filename}" if task.filename else f"Task {index}"
            heading_run = anchor.add_run(title)
            heading_run.bold = True
            heading_run.font.size = Pt(14)

            if task.description:
                anchor = insert_paragraph_after(anchor)
                anchor.add_run(task.description)

            if has_code:
                anchor = insert_paragraph_after(anchor)
                anchor.add_run("Implementation:").bold = True
                if as_text:
                    # Real, selectable monospaced text -- never an image of code.
                    anchor = self._insert_ide_block_after(anchor, task.code, light=True)
                else:
                    anchor = self._write_terminal_image(anchor, code_screenshots.get(task.id), task.code)

            if runnable:
                anchor = insert_paragraph_after(anchor)
                anchor.add_run("Execution Output:").bold = True
                anchor = self._write_task_output(anchor, screenshots.get(task.id), results_by_task.get(task.id))

            if task.explanation.strip():
                anchor = insert_paragraph_after(anchor)
                anchor.add_run("Explanation:").bold = True
                anchor = insert_paragraph_after(anchor)
                anchor.add_run(task.explanation.strip())

            anchor = insert_paragraph_after(anchor)
            anchor.add_run()

        for table in generated_lab.tables:
            anchor = self._write_table(anchor, table)

        if generated_lab.screenshots:
            anchor = self._write_screenshot_slots(anchor, generated_lab.screenshots)

        if generated_lab.conclusion.strip():
            anchor = insert_paragraph_after(anchor)
            self._heading_run(anchor, "Conclusion")
            anchor = insert_paragraph_after(anchor)
            anchor.add_run(generated_lab.conclusion.strip())

        remove_paragraph(target)

    @staticmethod
    def _heading_run(paragraph, text: str) -> None:
        run = paragraph.add_run(text)
        run.bold = True
        run.font.size = Pt(14)
        paragraph.paragraph_format.keep_with_next = True  # never strand a heading at a page bottom

    def _write_terminal_image(self, anchor, screenshot_b64: str | None, fallback_text: str):
        """Embeds a rendered image of the code, or degrades to the IDE block table."""
        if screenshot_b64:
            try:
                image_bytes = base64.b64decode(screenshot_b64)
                next_anchor = insert_paragraph_after(anchor)
                next_anchor.add_run().add_picture(io.BytesIO(image_bytes), width=_SCREENSHOT_WIDTH)
                return next_anchor
            except (binascii.Error, UnrecognizedImageError, ValueError):
                pass 
        return self._insert_ide_block_after(anchor, fallback_text)

    def _insert_ide_block_after(self, anchor, text: str, light: bool = False):
        """Fallback: Inserts a 1x1 table with a VS Code dark background."""
        next_anchor = insert_paragraph_after(anchor)
        tbl = anchor._parent.add_table(rows=1, cols=1, width=Inches(6.0))
        anchor._p.addnext(tbl._tbl)
        
        cell = tbl.cell(0, 0)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'F3F3F3' if light else '1E1E1E')
        tcPr.append(shd)
        if light:
            self._set_table_borders(tbl, color="BFBFBF")
        
        cell.text = ""
        para = cell.paragraphs[0]
        run = para.add_run()
        run.font.name = _CODE_FONT
        run.font.size = _CODE_SIZE
        run.font.color.rgb = RGBColor(0x1F, 0x1F, 0x1F) if light else RGBColor(0xD4, 0xD4, 0xD4)

        lines = text.replace("\r\n", "\n").replace("\t", "    ").split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                run.add_break(WD_BREAK.LINE)
            run.add_text(line)
        return next_anchor

    def _write_task_output(self, anchor, screenshot_b64: str | None, result: ExecutionResult | None):
        """Embeds the screenshot, or degrades to an IDE-styled text block safely."""
        if screenshot_b64:
            try:
                image_bytes = base64.b64decode(screenshot_b64)
                next_anchor = insert_paragraph_after(anchor)
                next_anchor.add_run().add_picture(io.BytesIO(image_bytes), width=_SCREENSHOT_WIDTH)
                return next_anchor
            except (binascii.Error, UnrecognizedImageError, ValueError):
                pass 

        if result is not None and result.status in _TEXT_FALLBACK_STATUSES:
            text = result.stdout if result.status == ExecutionStatus.SUCCESS else result.stderr
            fallback_text = text.strip() or "(no terminal output)"
            return self._insert_ide_block_after(anchor, fallback_text)

        next_anchor = insert_paragraph_after(anchor)
        next_anchor.add_run("(No execution output available)")
        return next_anchor

    # ------------------------------------------------------------------
    # Project / documentation assignment sections
    # ------------------------------------------------------------------
    @staticmethod
    def _set_table_borders(tbl, color: str = "808080", size: int = 4, dashed: bool = False) -> None:
        tbl_pr = tbl._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            element = OxmlElement(f"w:{edge}")
            element.set(qn("w:val"), "dashed" if dashed else "single")
            element.set(qn("w:sz"), str(size))
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), color)
            borders.append(element)
        look = tbl_pr.find(qn("w:tblLook"))  # schema order: borders come before tblLook
        if look is not None:
            look.addprevious(borders)
        else:
            tbl_pr.append(borders)

    @staticmethod
    def _shade_cell(cell, fill: str) -> None:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill)
        cell._tc.get_or_add_tcPr().append(shd)

    def _table_after(self, anchor, rows: int, cols: int):
        """Creates a table directly after `anchor`; returns (table, paragraph after it)."""
        next_anchor = insert_paragraph_after(anchor)
        tbl = anchor._parent.add_table(rows=rows, cols=cols, width=Inches(6.0))
        anchor._p.addnext(tbl._tbl)
        return tbl, next_anchor

    def _write_steps(self, anchor, steps):
        anchor = insert_paragraph_after(anchor)
        self._heading_run(anchor, "Steps Performed")
        for number, step in enumerate(steps, start=1):
            anchor = insert_paragraph_after(anchor)
            head = anchor.add_run(f"{number}. {step.title}".rstrip() if step.title else f"{number}.")
            head.bold = True
            for label, value in (
                ("What I did", step.details),
                ("Where", step.location),
                ("Common issue and fix", step.issue),
            ):
                if value.strip():
                    anchor = insert_paragraph_after(anchor)
                    anchor.paragraph_format.left_indent = Inches(0.3)
                    anchor.add_run(f"{label}: ").italic = True
                    anchor.add_run(value.strip())
        return insert_paragraph_after(anchor)

    def _write_table(self, anchor, table: LabTable):
        if table.title:
            anchor = insert_paragraph_after(anchor)
            self._heading_run(anchor, table.title)
        columns = max([len(table.headers), *(len(row) for row in table.rows)] or [0])
        if columns == 0:
            return anchor
        rows = ([table.headers] if table.headers else []) + table.rows
        tbl, next_anchor = self._table_after(anchor, rows=len(rows), cols=columns)
        self._set_table_borders(tbl)
        for r_index, row in enumerate(rows):
            for c_index in range(columns):
                text = row[c_index] if c_index < len(row) else ""
                cell = tbl.cell(r_index, c_index)
                cell.text = ""
                run = cell.paragraphs[0].add_run(text)
                run.font.size = Pt(10)
                if table.headers and r_index == 0:
                    run.bold = True
                    self._shade_cell(cell, "D9E2F3")
        return next_anchor

    def _write_screenshot_slots(self, anchor, captions: list[str]):
        anchor = insert_paragraph_after(anchor)
        self._heading_run(anchor, "Screenshots")
        for number, caption in enumerate(captions, start=1):
            tbl, next_anchor = self._table_after(anchor, rows=1, cols=1)
            self._set_table_borders(tbl, color="999999", dashed=True)
            row = tbl.rows[0]
            tr_pr = row._tr.get_or_add_trPr()
            height = OxmlElement("w:trHeight")
            height.set(qn("w:val"), str(int(2.4 * 1440)))
            height.set(qn("w:hRule"), "atLeast")
            tr_pr.append(height)
            cell = tbl.cell(0, 0)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run("[ Insert your screenshot here ]")
            run.italic = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

            label = next_anchor
            label.alignment = WD_ALIGN_PARAGRAPH.CENTER
            caption_run = label.add_run(f"Figure {number}: {caption}")
            caption_run.italic = True
            caption_run.font.size = Pt(10)
            anchor = label
        return insert_paragraph_after(anchor)

