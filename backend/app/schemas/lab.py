"""Ported from src/types/lab.ts.

None of these are wired into the pipeline yet — same as in the original
repo, they exist so later phases (parser, AI adapter, executor, docx
generator) have an agreed shape to target.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LabTask(BaseModel):
    id: str
    description: str
    language: Optional[str] = None


class ParsedLab(BaseModel):
    title: Optional[str] = None
    raw_text: str
    tasks: list[LabTask]


class GeneratedTaskSolution(BaseModel):
    id: str
    description: str
    language: str
    filename: str
    code: str
    explanation: str


class LabStep(BaseModel):
    """One numbered step of a "steps performed" section."""

    title: str = ""
    details: str = ""
    location: str = ""  # where in the tool/IDE the step is done
    issue: str = ""  # a COMMON issue and its fix (never claimed as the student's own)


class LabTable(BaseModel):
    """A table the lab asks the student to fill in (e.g. lifecycle callbacks)."""

    title: str = ""
    headers: list[str] = []
    rows: list[list[str]] = []


class GeneratedLab(BaseModel):
    lab_title: str
    objectives: list[str]
    tasks: list[GeneratedTaskSolution]
    conclusion: str
    # --- project / documentation assignments (all optional, default empty) ---
    steps: list[LabStep] = []
    tables: list[LabTable] = []
    # Captions of screenshots the student must take; rendered as empty frames
    # for the student to fill. The app never invents screenshots of tools it
    # cannot run (an Android emulator, a browser, an IDE).
    screenshots: list[str] = []
    # Paste code as real text (monospaced) instead of an image of the code.
    code_as_text: bool = False


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNSUPPORTED = "unsupported"


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
