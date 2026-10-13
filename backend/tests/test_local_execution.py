"""Real, unmocked tests for the local (non-Docker) execution backend."""

import os
import shutil

import pytest

from app.core.config import settings
from app.execution import get_executor
from app.schemas.lab import ExecutionStatus


@pytest.fixture(autouse=True)
def _local_mode(monkeypatch):
    monkeypatch.setattr(settings, "code_execution_enabled", True)
    monkeypatch.setattr(settings, "code_execution_mode", "local")
    monkeypatch.setattr(settings, "code_execution_timeout_seconds", 3)
    monkeypatch.setattr(settings, "code_compile_timeout_seconds", 30)


@pytest.mark.asyncio
async def test_python_success_captures_real_stdout():
    result = await get_executor("python").execute("print(sum(range(10)))")
    assert result.status == ExecutionStatus.SUCCESS
    assert result.stdout.strip() == "45"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_python_runtime_error_is_failed_with_traceback():
    result = await get_executor("python").execute("1/0")
    assert result.status == ExecutionStatus.FAILED
    assert "ZeroDivisionError" in result.stderr


@pytest.mark.asyncio
async def test_python_timeout_is_reported_and_process_killed():
    result = await get_executor("python").execute("while True: pass")
    assert result.status == ExecutionStatus.TIMEOUT


@pytest.mark.asyncio
async def test_input_does_not_hang():
    result = await get_executor("python").execute("name = input('Name: ')\nprint(name)")
    assert result.status == ExecutionStatus.FAILED
    assert "EOFError" in result.stderr


@pytest.mark.asyncio
async def test_output_is_truncated():
    result = await get_executor("python").execute("print('x' * 100000)")
    assert result.status == ExecutionStatus.SUCCESS
    assert "[...output truncated...]" in result.stdout
    assert len(result.stdout) < 25_000


@pytest.mark.asyncio
async def test_server_secrets_are_not_inherited(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "super-secret-key")
    code = "import os\nprint(os.environ.get('AI_API_KEY', 'MISSING'))"
    result = await get_executor("python").execute(code)
    assert result.stdout.strip() == "MISSING"


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")
@pytest.mark.asyncio
async def test_cpp_compiles_and_runs():
    code = '#include <iostream>\nint main(){ std::cout << "hi " << 6*7 << std::endl; }'
    result = await get_executor("cpp").execute(code)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.stdout.strip() == "hi 42"


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc not installed")
@pytest.mark.asyncio
async def test_c_is_compiled_as_c_not_cpp():
    code = '#include <stdio.h>\nint main(void){ printf("c ok\\n"); return 0; }'
    result = await get_executor("c").execute(code)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.stdout.strip() == "c ok"


@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")
@pytest.mark.asyncio
async def test_compile_error_is_reported_as_failed():
    result = await get_executor("cpp").execute("int main( { return 0; }")
    assert result.status == ExecutionStatus.FAILED
    assert "error" in result.stderr.lower()


@pytest.mark.asyncio
async def test_unsupported_language_still_unsupported():
    result = await get_executor("java").execute("class A {}")
    assert result.status == ExecutionStatus.UNSUPPORTED


@pytest.mark.asyncio
async def test_disabled_flag_wins_over_local_mode(monkeypatch):
    monkeypatch.setattr(settings, "code_execution_enabled", False)
    result = await get_executor("python").execute("print(1)")
    assert result.status == ExecutionStatus.UNSUPPORTED


@pytest.mark.asyncio
async def test_traceback_does_not_leak_the_server_temp_path():
    result = await get_executor("python").execute("print(undefined_name)")
    assert "labmate-exec-" not in result.stderr
    assert 'File "main.py"' in result.stderr


@pytest.mark.skipif(os.geteuid() != 0, reason="privilege drop only applies when the server runs as root")
@pytest.mark.asyncio
async def test_code_runs_unprivileged_and_cannot_read_server_secrets(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "super-secret-key")
    code = (
        "import os\n"
        "print('uid', os.getuid())\n"
        "try:\n"
        "    data = open(f'/proc/{os.getppid()}/environ','rb').read()\n"
        "    print('LEAK' if b'super-secret-key' in data else 'readable-but-clean')\n"
        "except Exception as e:\n"
        "    print('blocked', type(e).__name__)\n"
        "try:\n"
        "    open('/etc/labmate-pwned','w')\n"
        "    print('WROTE-ETC')\n"
        "except Exception as e:\n"
        "    print('etc-blocked', type(e).__name__)\n"
    )
    result = await get_executor("python").execute(code)
    assert "uid 65534" in result.stdout
    assert "LEAK" not in result.stdout
    assert "blocked PermissionError" in result.stdout
    assert "WROTE-ETC" not in result.stdout
