import io

import pytest
from docx import Document
from reportlab.pdfgen import canvas


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(72, 800, "Lab 04: Constraint Satisfaction Problems")
    c.drawString(72, 780, "Objective: Model the N-Queens problem as a CSP.")
    c.drawString(72, 760, "Task 1: Formulate variables, domains, and constraints.")
    c.save()
    return buffer.getvalue()


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """A structurally valid PDF with no text layer (simulates a scan)."""
    buffer = io.BytesIO()
    canvas.Canvas(buffer).save()
    return buffer.getvalue()


@pytest.fixture
def sample_docx_bytes() -> bytes:
    buffer = io.BytesIO()
    document = Document()
    document.add_heading("Lab 03: Prolog Basics", level=1)
    document.add_paragraph("Objective: Understand facts and rules in Prolog.")
    document.add_paragraph("Task 1: Write a Prolog program for family relationships.")
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def empty_docx_bytes() -> bytes:
    buffer = io.BytesIO()
    Document().save(buffer)
    return buffer.getvalue()
