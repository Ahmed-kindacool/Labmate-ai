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

_DOCKER_IMAGE = "python:3.11-slim"
_CPU_LIMIT = "0.5"
_MEMORY_LIMIT = "256m"
_PIDS_LIMIT = "50"


class PythonExecutor:
    """Executes Python code inside a disposable, network-isolated Docker
    container. Mirrors the command Dev C sketched in the original stub:

        docker run --rm --network none --cpus="0.5" --memory="256m" \\
            --pids-limit=50 -v /tmp/code:/app python:3.9-slim python /app/main.py

    with the safety gaps closed: real timeout enforcement (including
    killing the container if the client-side process is killed on
    timeout — `--rm` alone doesn't help if the container is still running
    server-side), output-size capping, and a graceful "disabled" result
    instead of ever falling back to running code directly on the host.

    Per PROJECT_SPEC.md §4: "If safe sandboxing is unavailable in a
    deployment environment, execution should be disabled rather than
    performed unsafely." That's enforced here, not just documented —
    see `_availability_error()`.
    """

    async def execute(self, code: str) -> ExecutionResult:
        unavailable = self._availability_error()
        if unavailable:
            return unavailable

        container_name = f"labemate-exec-{uuid.uuid4().hex[:12]}"

        with tempfile.TemporaryDirectory(prefix="labemate-exec-") as tmp_dir:
            code_path = Path(tmp_dir) / "main.py"
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
                "--workdir",
                "/app",
                _DOCKER_IMAGE,
                "python",
                "/app/main.py",
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
                    stderr=f"Execution sandbox error: {exc}",
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
                timeout=settings.code_execution_timeout_seconds,
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
