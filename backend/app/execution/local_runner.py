"""Runs student code as a locked-down child process of the server.

Cross-platform: Linux/macOS (production, Docker image) and Windows (local
development). It uses blocking `subprocess.Popen` inside a worker thread rather
than asyncio subprocesses, so it works on every event loop -- including the
Windows SelectorEventLoop that `uvicorn --reload` uses, where asyncio
subprocesses raise NotImplementedError.

Protections by platform
-----------------------
Linux/macOS (what the Docker image uses; NOT as strong as the docker backend --
there is no network namespace):
* fresh empty working directory per run, deleted afterwards
* minimal environment (no API keys, nothing inherited)
* privileges dropped to uid 65534 ("nobody") when the server runs as root, so
  the code cannot read the server's /proc/<pid>/environ or secrets
* rlimits: CPU seconds, address space, file size, open files, no core dumps
* own session, whole process group killed on timeout
Windows (development only): fresh working dir, minimal environment, timeout,
process-tree kill, output cap. No rlimits, no privilege drop -- run untrusted
labs in the Docker image instead.
All platforms: stdin closed (input() raises EOFError instead of hanging).
"""

import asyncio
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from app.core.config import settings
from app.schemas.lab import ExecutionResult, ExecutionStatus

IS_WINDOWS = os.name == "nt"
if not IS_WINDOWS:
    import resource

MAX_OUTPUT_CHARS = 20_000
_UNPRIVILEGED_UID = 65534  # nobody
_UNPRIVILEGED_GID = 65534
_RUN_MEMORY_BYTES = 512 * 1024 * 1024
_MAX_FILE_BYTES = 10 * 1024 * 1024


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n[...output truncated...]"


def _minimal_env(home: str) -> dict[str, str]:
    if IS_WINDOWS:
        # Python and MinGW tools need SYSTEMROOT/PATH to start at all.
        return {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "TEMP": home,
            "TMP": home,
            "HOME": home,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": home,
        "TMPDIR": home,
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }


def _should_drop_privileges() -> bool:
    return (not IS_WINDOWS) and hasattr(os, "geteuid") and os.geteuid() == 0


def _make_preexec(cpu_seconds: int, limit_memory: bool, drop_privileges: bool):
    def _apply() -> None:
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (_MAX_FILE_BYTES, _MAX_FILE_BYTES))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if limit_memory:
            resource.setrlimit(resource.RLIMIT_AS, (_RUN_MEMORY_BYTES, _RUN_MEMORY_BYTES))
        if drop_privileges:
            os.setgroups([])
            os.setgid(_UNPRIVILEGED_GID)
            os.setuid(_UNPRIVILEGED_UID)

    return _apply


def _kill_tree(process: subprocess.Popen) -> None:
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            process.kill()
        except OSError:
            pass


def _run_blocking(
    argv: list[str],
    cwd: str,
    env: dict[str, str],
    timeout: float,
    *,
    limit_memory: bool,
    drop_privileges: bool,
) -> tuple[int | None, bytes, bytes, bool]:
    """Returns (returncode, stdout, stderr, timed_out). Runs in a worker thread."""
    kwargs: dict = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kwargs["preexec_fn"] = _make_preexec(int(timeout) + 1, limit_memory, drop_privileges)

    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )
    try:
        out, err = process.communicate(timeout=timeout)
        return process.returncode, out, err, False
    except subprocess.TimeoutExpired:
        _kill_tree(process)
        try:
            process.communicate(timeout=3)
        except Exception:  # noqa: BLE001 - already killed; just reap
            pass
        return None, b"", b"", True


async def _run(argv, cwd, env, timeout, *, limit_memory, drop_privileges):
    return await asyncio.to_thread(
        _run_blocking,
        argv,
        cwd,
        env,
        timeout,
        limit_memory=limit_memory,
        drop_privileges=drop_privileges,
    )


def _timeout_result(seconds: float, what: str = "Execution") -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus.TIMEOUT,
        stdout="",
        stderr=f"{what} exceeded the {seconds:g}s time limit and was stopped.",
        exit_code=None,
    )


def _prepare_dir(tmp_dir: str, drop: bool) -> None:
    if IS_WINDOWS:
        return
    os.chmod(tmp_dir, 0o755)
    if drop:
        os.chown(tmp_dir, _UNPRIVILEGED_UID, _UNPRIVILEGED_GID)


def _write_source(tmp_dir: str, name: str, code: str, drop: bool) -> Path:
    path = Path(tmp_dir) / name
    path.write_text(code, encoding="utf-8")
    if not IS_WINDOWS:
        os.chmod(path, 0o644)
        if drop:
            os.chown(path, _UNPRIVILEGED_UID, _UNPRIVILEGED_GID)
    return path


def _clean(text: bytes, tmp_dir: str) -> str:
    """Decode, cap, and hide the server's temp path (tracebacks would
    otherwise print File "/tmp/labmate-exec-xyz/main.py")."""
    decoded = text.decode("utf-8", errors="replace")
    for variant in (tmp_dir + os.sep, tmp_dir + "/", tmp_dir + "\\"):
        decoded = decoded.replace(variant, "")
    return _truncate(decoded)


def _finish(returncode: int | None, out: bytes, err: bytes, tmp_dir: str) -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus.SUCCESS if returncode == 0 else ExecutionStatus.FAILED,
        stdout=_clean(out, tmp_dir),
        stderr=_clean(err, tmp_dir),
        exit_code=returncode,
    )


async def run_python_local(code: str) -> ExecutionResult:
    drop = _should_drop_privileges()
    timeout = settings.code_execution_timeout_seconds
    with tempfile.TemporaryDirectory(prefix="labmate-exec-") as tmp_dir:
        _prepare_dir(tmp_dir, drop)
        _write_source(tmp_dir, "main.py", code, drop)
        returncode, out, err, timed_out = await _run(
            [sys.executable, "-I", "main.py"],
            tmp_dir,
            _minimal_env(tmp_dir),
            timeout,
            limit_memory=True,
            drop_privileges=drop,
        )
        if timed_out:
            return _timeout_result(timeout)
        return _finish(returncode, out, err, tmp_dir)


def find_compiler(language: str) -> str | None:
    names = ("gcc", "cc") if language == "c" else ("g++", "c++")
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _no_compiler_result(language: str) -> ExecutionResult:
    label = "C" if language == "c" else "C++"
    hint = " (on Windows install MinGW-w64/MSYS2 and add it to PATH)" if IS_WINDOWS else ""
    return ExecutionResult(
        status=ExecutionStatus.UNSUPPORTED,
        stdout="",
        stderr=f"No {label} compiler is installed on this server{hint}.",
        exit_code=None,
    )


async def run_c_family_local(code: str, language: str) -> ExecutionResult:
    """Compile (own time budget) then run (execution time budget)."""
    compiler = find_compiler(language)
    if compiler is None:
        return _no_compiler_result(language)

    drop = _should_drop_privileges()
    run_timeout = settings.code_execution_timeout_seconds
    compile_timeout = settings.code_compile_timeout_seconds
    source = "main.c" if language == "c" else "main.cpp"
    binary = "main.exe" if IS_WINDOWS else "main"

    with tempfile.TemporaryDirectory(prefix="labmate-exec-") as tmp_dir:
        _prepare_dir(tmp_dir, drop)
        _write_source(tmp_dir, source, code, drop)
        env = _minimal_env(tmp_dir)

        # Compilers need address space and sub-processes (cc1plus, as, ld), so
        # no memory limit applies while compiling.
        argv = [compiler, source, "-O0", "-o", binary]
        if language == "c":
            argv += ["-lm"]
        returncode, out, err, timed_out = await _run(
            argv, tmp_dir, env, compile_timeout, limit_memory=False, drop_privileges=drop
        )
        if timed_out:
            return _timeout_result(compile_timeout, "Compilation")
        if returncode != 0:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                stdout=_clean(out, tmp_dir),
                stderr=_clean(err, tmp_dir),
                exit_code=returncode,
            )

        run_argv = [os.path.join(tmp_dir, binary)] if IS_WINDOWS else ["./" + binary]
        returncode, out, err, timed_out = await _run(
            run_argv, tmp_dir, env, run_timeout, limit_memory=True, drop_privileges=drop
        )
        if timed_out:
            return _timeout_result(run_timeout)
        return _finish(returncode, out, err, tmp_dir)
