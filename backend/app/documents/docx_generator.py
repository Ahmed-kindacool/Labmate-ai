import base64
import binascii
import io
import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK
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
from app.schemas.lab import ExecutionResult, ExecutionStatus, GeneratedLab
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
        self._build_sequential_content(document, generated_lab.tasks, results_by_task, screenshots, code_screenshots)

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

    def _build_sequential_content(self, document: Document, tasks: list, results_by_task: dict, screenshots: dict, code_screenshots: dict) -> None:
        target = find_placeholder_paragraph(document, "{{LAB_CONTENT}}")
        if target is None:
            return

        anchor = target
        for index, task in enumerate(tasks, start=1):
            anchor = insert_paragraph_after(anchor)
            heading_run = anchor.add_run(f"Task {index}: {task.filename}")
            heading_run.bold = True
            heading_run.font.size = Pt(14)

            if task.description:
                anchor = insert_paragraph_after(anchor)
                anchor.add_run(task.description)

            anchor = insert_paragraph_after(anchor)
            anchor.add_run("Implementation:").bold = True
            
            if task.code.strip():
                anchor = self._write_terminal_image(anchor, code_screenshots.get(task.id), task.code)
            else:
                anchor = insert_paragraph_after(anchor)
                anchor.add_run("(No code provided)")

            anchor = insert_paragraph_after(anchor)
            anchor.add_run("Execution Output:").bold = True
            
            anchor = self._write_task_output(anchor, screenshots.get(task.id), results_by_task.get(task.id))

            anchor = insert_paragraph_after(anchor)
            anchor.add_run()

        remove_paragraph(target)

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

    def _insert_ide_block_after(self, anchor, text: str):
        """Fallback: Inserts a 1x1 table with a VS Code dark background."""
        next_anchor = insert_paragraph_after(anchor)
        tbl = anchor._parent.add_table(rows=1, cols=1, width=Inches(6.0))
        anchor._p.addnext(tbl._tbl)
        
        cell = tbl.cell(0, 0)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), '1E1E1E') 
        tcPr.append(shd)
        
        cell.text = ""
        para = cell.paragraphs[0]
        run = para.add_run()
        run.font.name = _CODE_FONT
        run.font.size = _CODE_SIZE
        run.font.color.rgb = RGBColor(0xD4, 0xD4, 0xD4)
        
        lines = text.split("\n")
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