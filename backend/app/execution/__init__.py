<<<<<<< HEAD
from app.execution.executor import CodeExecutor
from app.execution.factory import get_executor

__all__ = ["CodeExecutor", "get_executor"]
=======
import docker
import tempfile
import os
from pydantic import BaseModel
from typing import Optional

class ExecutionResult(BaseModel):
    output: str
    success: bool
    error: Optional[str] = None

class CodeExecutor:
    async def execute(self, code: str) -> ExecutionResult:
        raise NotImplementedError("Executor strategy not defined.")

class PythonExecutor(CodeExecutor):
    async def execute(self, code: str) -> ExecutionResult:
        # Connect to the Docker Engine running on your system
        client = docker.from_env()
        
        # Create a temporary directory that automatically deletes itself
        with tempfile.TemporaryDirectory() as temp_dir:
            code_path = os.path.join(temp_dir, "script.py")
            with open(code_path, "w") as f:
                f.write(code)

            try:
                # Spin up an isolated container with strict resource limits
                output_bytes = client.containers.run(
                    image="python:3.11-slim",
                    command="python /app/script.py",
                    volumes={temp_dir: {'bind': '/app', 'mode': 'ro'}},
                    network_mode="none",
                    mem_limit="256m",
                    nano_cpus=500000000,  # 0.5 CPU cores
                    pids_limit=50,
                    remove=True,
                    stdout=True,
                    stderr=True
                )
                return ExecutionResult(output=output_bytes.decode('utf-8'), success=True)
                
            except docker.errors.ContainerError as e:
                # If the student's code throws an error (e.g., SyntaxError), capture it
                error_output = e.stderr.decode('utf-8') if e.stderr else str(e)
                return ExecutionResult(output=error_output, success=False, error="Runtime Error")
            except docker.errors.ImageNotFound:
                # Fallback if the image hasn't been pulled yet
                return ExecutionResult(output="", success=False, error="Docker image python:3.11-slim not found. Run 'docker pull python:3.11-slim'.")
>>>>>>> 6aaba64b0d244d05562e6b3cf1ebaa54dc5da329
