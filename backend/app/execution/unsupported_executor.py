from app.schemas.lab import ExecutionResult, ExecutionStatus


class UnsupportedExecutor:
    """Returned by the factory for any language with no executor yet
    (README.md: "Start with Python support. If practical, add C++ and Java
    afterward. Unsupported languages should not crash the application.").

    This is a normal, expected outcome — not an error — so it returns a
    plain ExecutionResult rather than raising.
    """

    def __init__(self, language: str) -> None:
        self._language = language

    async def execute(self, code: str) -> ExecutionResult:
        del code  # never executed — that's the point of "unsupported"
        return ExecutionResult(
            status=ExecutionStatus.UNSUPPORTED,
            stdout="",
            stderr=f"Code execution for '{self._language}' isn't supported yet.",
            exit_code=None,
        )
