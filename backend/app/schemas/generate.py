from typing import Literal, Optional, Union

from pydantic import BaseModel

from app.schemas.lab import ExecutionResult, GeneratedLab

# Ported from `GenerateErrorResponse["code"]` in src/types/api.ts.
AppErrorCode = Literal[
    "INVALID_INPUT",
    "UNSUPPORTED_FILE",
    "FILE_TOO_LARGE",
    "LAB_READ_FAILED",
    "AI_GENERATION_FAILED",
    "EXECUTION_FAILED",
    "REPORT_GENERATION_FAILED",
]


class TaskExecutionResult(BaseModel):
    """Pairs a GeneratedTaskSolution.id with its ExecutionResult, so the
    frontend can match execution output back to the right task card."""

    task_id: str
    result: ExecutionResult


class GenerateSuccessResponse(BaseModel):
    status: Literal["success"] = "success"
    # Placeholder until Phase 7 (real DOCX generation) — same as the
    # original mock. See docs/API_CONTRACT.md "Open question".
    download_url: str
    # Phase 3: the AI's structured output, so the frontend can render
    # question/explanation/code sections before the DOCX pipeline exists.
    # NOTE for Dev A: this serializes snake_case (lab_title, raw_text, ...)
    # per the project's existing convention (see StudentInfo). Update
    # frontend/src/types/lab.ts's `labTitle` -> `lab_title` to match before
    # wiring this up — everything else in that file already matches.
    generated_lab: Optional[GeneratedLab] = None
    # Phase 4: one entry per task that had code to run. NOTE for Dev A:
    # same snake_case note as above applies to `exitCode` -> `exit_code`
    # in frontend/src/types/lab.ts's ExecutionResult.
    execution_results: Optional[list[TaskExecutionResult]] = None
    # Phase 5: base64-encoded PNG terminal screenshots, keyed by task_id,
    # for tasks whose execution produced real output (success or a real
    # failure — see app/screenshots/service.py). This is primarily for
    # Phase 7 (DOCX embedding) and manual verification — the live frontend
    # preview (report-preview.tsx) re-renders the terminal from raw text
    # client-side rather than displaying this image, so nothing here is a
    # frontend blocker.
    screenshots: Optional[dict[str, str]] = None


class GenerateErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    code: AppErrorCode
    message: str
    # Present only for INVALID_INPUT, same as the original contract.
    field_errors: Optional[dict[str, list[str]]] = None


GenerateResponse = Union[GenerateSuccessResponse, GenerateErrorResponse]
