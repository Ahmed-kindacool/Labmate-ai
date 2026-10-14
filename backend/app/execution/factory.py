from app.execution.executor import CodeExecutor
from app.execution.python_executor import PythonExecutor
from app.execution.cpp_executor import CppExecutor
from app.execution.unsupported_executor import UnsupportedExecutor

_PYTHON_ALIASES = {"python", "python3", "py"}
_CPP_ALIASES = {"cpp", "c++", "c"}


def get_executor(language: str) -> CodeExecutor:
    """Strategy dispatch per ARCHITECTURE.md's CodeExecutor pattern.
    README.md: start with Python; add C++/Java later without touching
    this call site — just add another branch and an aliases set.
    """
    normalized = language.strip().lower()
    if normalized in _PYTHON_ALIASES:
        return PythonExecutor()
    elif normalized in _CPP_ALIASES:
        return CppExecutor("c" if normalized == "c" else "cpp")
    return UnsupportedExecutor(language)


def is_runnable_language(language: str) -> bool:
    """True for languages the report generator can really execute.

    Anything else (xml, java, kotlin, html, sql, ...) is shown as source code
    only -- there is no execution output to show or to invent.
    """
    normalized = language.strip().lower()
    return normalized in _PYTHON_ALIASES or normalized in _CPP_ALIASES
