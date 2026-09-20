from typing import Protocol

from app.schemas.lab import ExecutionResult


class CodeExecutor(Protocol):
    """Strategy interface per ARCHITECTURE.md's CodeExecutor pattern
    (PythonExecutor, CppExecutor, JavaExecutor, UnsupportedExecutor).

    Every implementation must return an ExecutionResult, never raise for
    the code itself failing/timing out/being unsupported — those are
    ordinary outcomes recorded in `status`, not exceptions. This matters
    for the anti-fabrication rule in AI_AND_GENERATION.md: a failed
    execution still produces a real report section (a reported failure),
    not a fabricated success.
    """

    async def execute(self, code: str) -> ExecutionResult: ...
