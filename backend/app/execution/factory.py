from app.execution.executor import CodeExecutor
from app.execution.python_executor import PythonExecutor
from app.execution.unsupported_executor import UnsupportedExecutor

_PYTHON_ALIASES = {"python", "python3", "py"}


def get_executor(language: str) -> CodeExecutor:
    """Strategy dispatch per ARCHITECTURE.md's CodeExecutor pattern.
    README.md: start with Python; add C++/Java later without touching
    this call site — just add another branch and an aliases set.
    """
    normalized = language.strip().lower()
    if normalized in _PYTHON_ALIASES:
        return PythonExecutor()
    return UnsupportedExecutor(language)
