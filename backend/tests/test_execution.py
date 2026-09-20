import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.execution.factory import get_executor
from app.execution.python_executor import PythonExecutor
from app.execution.unsupported_executor import UnsupportedExecutor
from app.schemas.lab import ExecutionStatus


class TestFactory:
    @pytest.mark.parametrize("language", ["python", "Python", "PYTHON", "python3", "py"])
    def test_routes_python_aliases_to_python_executor(self, language: str) -> None:
        assert isinstance(get_executor(language), PythonExecutor)

    @pytest.mark.parametrize("language", ["cpp", "java", "javascript", "", "prolog"])
    def test_routes_everything_else_to_unsupported(self, language: str) -> None:
        assert isinstance(get_executor(language), UnsupportedExecutor)


class TestUnsupportedExecutor:
    @pytest.mark.asyncio
    async def test_never_executes_and_reports_unsupported(self) -> None:
        executor = UnsupportedExecutor("cobol")
        result = await executor.execute("some code")

        assert result.status == ExecutionStatus.UNSUPPORTED
        assert result.stdout == ""
        assert "cobol" in result.stderr


class TestPythonExecutorAvailability:
    """These exercise the REAL availability checks — no mocking — since
    this is exactly the safety-critical path from PROJECT_SPEC.md §4:
    "If safe sandboxing is unavailable... execution should be disabled
    rather than performed unsafely." Must never fall through to running
    code directly on the host.
    """

    @pytest.mark.asyncio
    async def test_disabled_by_default_returns_unsupported(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", False)
        executor = PythonExecutor()

        result = await executor.execute("print('hello')")

        assert result.status == ExecutionStatus.UNSUPPORTED
        assert "disabled" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_enabled_but_no_docker_returns_unsupported(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", True)
        monkeypatch.setattr("shutil.which", lambda _name: None)
        executor = PythonExecutor()

        result = await executor.execute("print('hello')")

        assert result.status == ExecutionStatus.UNSUPPORTED
        assert "docker" in result.stderr.lower()


class _FakeProcess:
    def __init__(self, stdout: bytes, stderr: bytes, returncode: int, hang: bool = False) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self._hang = hang
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hang:
            await asyncio.sleep(10)
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.killed = True


class TestPythonExecutorSandboxedRun:
    """Docker itself isn't available in CI/dev sandboxes here, so these
    mock asyncio.create_subprocess_exec — the same technique used for the
    OpenAI SDK in test_openai_provider.py. The availability tests above
    cover the real, unmocked "no Docker" path.
    """

    @pytest.mark.asyncio
    async def test_successful_execution(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", True)
        monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/docker")
        fake_process = _FakeProcess(stdout=b"hello world\n", stderr=b"", returncode=0)

        with patch(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=fake_process)
        ) as mock_exec:
            result = await PythonExecutor().execute("print('hello world')")

        assert result.status == ExecutionStatus.SUCCESS
        assert result.stdout == "hello world\n"
        assert result.exit_code == 0
        # Confirms the safety flags are actually present on the command.
        args = mock_exec.call_args.args
        assert "--network" in args and "none" in args
        assert any(a.startswith("--memory=") for a in args)
        assert any(a.startswith("--cpus=") for a in args)
        assert any(a.startswith("--pids-limit=") for a in args)
        assert "--read-only" in args

    @pytest.mark.asyncio
    async def test_nonzero_exit_is_failed_not_an_exception(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", True)
        monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/docker")
        fake_process = _FakeProcess(stdout=b"", stderr=b"Traceback...\n", returncode=1)

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=fake_process)):
            result = await PythonExecutor().execute("raise ValueError()")

        assert result.status == ExecutionStatus.FAILED
        assert result.exit_code == 1
        assert "Traceback" in result.stderr

    @pytest.mark.asyncio
    async def test_timeout_kills_container_and_reports_timeout(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", True)
        monkeypatch.setattr(settings, "code_execution_timeout_seconds", 0.01)
        monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/docker")
        fake_process = _FakeProcess(stdout=b"", stderr=b"", returncode=0, hang=True)
        kill_process = MagicMock()
        kill_process.wait = AsyncMock(return_value=None)

        with patch(
            "asyncio.create_subprocess_exec",
            AsyncMock(side_effect=[fake_process, kill_process]),
        ) as mock_exec:
            result = await PythonExecutor().execute("while True: pass")

        assert result.status == ExecutionStatus.TIMEOUT
        assert fake_process.killed
        # Second call is the `docker kill <container_name>` cleanup.
        second_call_args = mock_exec.call_args_list[1].args
        assert second_call_args[:2] == ("docker", "kill")

    @pytest.mark.asyncio
    async def test_output_is_truncated(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", True)
        monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/docker")
        huge_output = b"x" * 30_000
        fake_process = _FakeProcess(stdout=huge_output, stderr=b"", returncode=0)

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=fake_process)):
            result = await PythonExecutor().execute("print('x' * 30000)")

        assert len(result.stdout) < 30_000
        assert "truncated" in result.stdout

    @pytest.mark.asyncio
    async def test_sandbox_error_is_reported_not_raised(self, monkeypatch) -> None:
        monkeypatch.setattr(settings, "code_execution_enabled", True)
        monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/docker")

        with patch(
            "asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError("docker daemon down"))
        ):
            result = await PythonExecutor().execute("print('hi')")

        assert result.status == ExecutionStatus.FAILED
        assert "docker daemon down" in result.stderr
