import io
import os
from pathlib import Path

import pytest
from docx import Document
from reportlab.pdfgen import canvas

from app.schemas.lab import GeneratedLab, GeneratedTaskSolution, ParsedLab


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


@pytest.fixture
def sample_parsed_lab() -> ParsedLab:
    return ParsedLab(
        title="Lab 03: Prolog Basics",
        raw_text=(
            "Lab 03: Prolog Basics\n"
            "Objective: Understand facts and rules in Prolog.\n"
            "Task 1: Write a Prolog program for family relationships."
        ),
        tasks=[],
    )


@pytest.fixture
def sample_generated_lab() -> GeneratedLab:
    return GeneratedLab(
        lab_title="Lab 03: Prolog Basics",
        objectives=["Understand facts and rules in Prolog."],
        tasks=[
            GeneratedTaskSolution(
                id="task-1",
                description="Write a Prolog program for family relationships.",
                language="prolog",
                filename="family.pl",
                code="parent(tom, bob).\nparent(bob, ann).",
                explanation="Defines parent facts to represent family relationships.",
            )
        ],
        conclusion="This lab covered basic Prolog facts and rules.",
    )


# Playwright's Python package insists on the exact browser revision it
# bundles, downloaded from Playwright's own CDN -- which this project's
# sandboxes generally can't reach (see docs/Screenshots.md's original
# "known limitation" and docs/PHASE9_TESTING.md). Some sandboxes do
# happen to have a real, if differently-versioned, Chromium build
# pre-installed for other purposes; this env var lets a real, unmocked
# Playwright test opt into using it instead of skipping.
_SANDBOX_CHROMIUM_PATH = os.environ.get("SANDBOX_CHROMIUM_PATH")


@pytest.fixture
def real_chromium_playwright(monkeypatch):
    """Monkeypatches `BrowserType.launch` (the class Playwright's real
    `chromium`/`firefox`/`webkit` objects are instances of) so that
    `chromium.launch()` -- called with no arguments, exactly as
    `ScreenshotService`/`generate_terminal_screenshot` call it -- resolves
    to this sandbox's Chromium binary instead of the exact bundled
    revision Playwright's Python package insists on. Everything else
    (the playwright instance, browser, context, page, and screenshot
    bytes produced) is 100% real, unpatched Playwright.

    Skips (doesn't fail) when no such binary is configured/available,
    since a real browser isn't something every environment has -- see
    `docs/PHASE9_TESTING.md` for how to set `SANDBOX_CHROMIUM_PATH`.
    """
    if not _SANDBOX_CHROMIUM_PATH or not Path(_SANDBOX_CHROMIUM_PATH).is_file():
        pytest.skip("SANDBOX_CHROMIUM_PATH not set to a real Chromium binary")

    from playwright.async_api import BrowserType

    original_launch = BrowserType.launch

    async def patched_launch(self, **kwargs):
        kwargs.setdefault("executable_path", _SANDBOX_CHROMIUM_PATH)
        return await original_launch(self, **kwargs)

    monkeypatch.setattr(BrowserType, "launch", patched_launch)
