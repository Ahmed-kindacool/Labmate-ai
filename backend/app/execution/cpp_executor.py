import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path

from app.core.config import settings
from app.schemas.lab import ExecutionResult, ExecutionStatus

# Hard ceiling independent of Docker's own limits — Docker bounds memory/CPU,
# not how much text a program can print. Without this, a runaway `print()`
# loop could still produce a multi-hundred-MB response body.
_MAX_OUTPUT_CHARS = 20_000

_DOCKER_IMAGE = "gcc:13"
_CPU_LIMIT = "0.5"
_MEMORY_LIMIT = "256m"
_PIDS_LIMIT = "50"


class CppExecutor:
    """Executes C++ code inside a disposable, network-isolated Docker
    container. Builds on the Python Docker sandbox blueprint but adds
    compilation step.
    """

    def __init__(self, language: str = "cpp") -> None:
        self._language = "c" if language.strip().lower() == "c" else "cpp"

    async def execute(self, code: str) -> ExecutionResult:
        if settings.code_execution_enabled and settings.code_execution_mode == "local":
            try:
                from app.execution.local_runner import run_c_family_local

                return await run_c_family_local(code, self._language)
            except Exception as exc:  # noqa: BLE001 - report, never crash the request
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    stdout="",
                    stderr=f"Execution sandbox error: {type(exc).__name__}: {exc}",
                    exit_code=None,
                )

        unavailable = self._availability_error()
        if unavailable:
            return unavailable

        container_name = f"labemate-exec-{uuid.uuid4().hex[:12]}"

        with tempfile.TemporaryDirectory(prefix="labemate-exec-") as tmp_dir:
            source_name = "main.c" if self._language == "c" else "main.cpp"
            code_path = Path(tmp_dir) / source_name
            code_path.write_text(code)

            command = [
                "docker",
                "run",
                "--rm",
                "--name",
                container_name,
                "--network",
                "none",
                f"--cpus={_CPU_LIMIT}",
                f"--memory={_MEMORY_LIMIT}",
                f"--pids-limit={_PIDS_LIMIT}",
                "--read-only",
                "-v",
                f"{tmp_dir}:/app:ro",
                "--tmpfs",
                "/tmp:rw,exec,mode=1777",
                "--workdir",
                "/app",
                _DOCKER_IMAGE,
                "sh",
                "-c",
                (
                    "gcc main.c -o /tmp/main -lm && /tmp/main"
                    if self._language == "c"
                    else "g++ main.cpp -o /tmp/main && /tmp/main"
                ),
            ]

            try:
                return await self._run(command, container_name)
            except Exception as exc:  # noqa: BLE001 - genuinely last-resort
                # Something went wrong with the sandbox itself (Docker
                # daemon died mid-run, etc.) rather than with the student's
                # code. Still a normal ExecutionResult, not a 500 — the
                # report should say "execution failed", not fabricate
                # output or crash the whole request.
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    stdout="",
                    stderr=f"Execution sandbox error: {type(exc).__name__}: {exc}",
                    exit_code=None,
                )

    async def _run(self, command: list[str], container_name: str) -> ExecutionResult:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                # Docker mode compiles and runs in one container, so the
                # budget is compile + run (a 5s total used to time out on
                # compilation alone).
                timeout=settings.code_execution_timeout_seconds
                + settings.code_compile_timeout_seconds,
            )
        except asyncio.TimeoutError:
            await self._force_kill(container_name, process)
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                stdout="",
                stderr=(
                    f"Execution exceeded the {settings.code_execution_timeout_seconds}s "
                    "time limit and was stopped."
                ),
                exit_code=None,
            )

        stdout = _truncate(stdout_bytes.decode(errors="replace"))
        stderr = _truncate(stderr_bytes.decode(errors="replace"))
        status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED

        return ExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            exit_code=process.returncode,
        )

    async def _force_kill(self, container_name: str, process: asyncio.subprocess.Process) -> None:
        """On timeout, killing our `docker run` client process does NOT
        stop the container running server-side in the Docker daemon —
        `--rm` only cleans up on normal exit. Without this, a timed-out
        script keeps burning CPU/memory in an orphaned container.
        """
        try:
            process.kill()
        except ProcessLookupError:
            pass

        kill_process = await asyncio.create_subprocess_exec(
            "docker",
            "kill",
            container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await kill_process.wait()

    def _availability_error(self) -> ExecutionResult | None:
        if not settings.code_execution_enabled:
            return ExecutionResult(
                status=ExecutionStatus.UNSUPPORTED,
                stdout="",
                stderr="Code execution is currently disabled on this server.",
                exit_code=None,
            )
        if shutil.which("docker") is None:
            return ExecutionResult(
                status=ExecutionStatus.UNSUPPORTED,
                stdout="",
                stderr=(
                    "Code execution is enabled but Docker isn't available on "
                    "this server. See docs/DEPLOYMENT.md."
                ),
                exit_code=None,
            )
        return None


def _truncate(text: str) -> str:
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    return text[:_MAX_OUTPUT_CHARS] + "\n[...output truncated...]"
