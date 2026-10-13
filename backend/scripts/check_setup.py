"""Checks your setup end to end WITHOUT the web UI.

    cd backend
    python scripts/check_setup.py

It (1) shows how your .env was read, (2) makes one real AI call with a tiny lab,
(3) runs the code the AI wrote and prints the real output. If something is
wrong, it prints the exact reason instead of a generic error.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.openai_provider import OpenAIProvider  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.execution import get_executor  # noqa: E402
from app.schemas.lab import ParsedLab  # noqa: E402

LAB_TEXT = """Lab 1: Basics
Task 1: Write a Python program that prints the squares of the numbers 1 to 5.
Task 2: Write a C++ program that prints the sum of the numbers 1 to 10.
"""


def ok(msg):
    print(f"[ OK ] {msg}")


def warn(msg):
    print(f"[WARN] {msg}")


def fail(msg):
    print(f"[FAIL] {msg}")


async def main() -> int:
    print("== 1. Configuration ==")
    key = settings.ai_api_key
    (ok if key else fail)(f"AI_API_KEY: {'set (' + key[:4] + '...)' if key else 'MISSING in backend/.env'}")
    print(f"       AI_BASE_URL: {settings.ai_base_url or '(default OpenAI)'}")
    print(f"       AI_MODEL:    {settings.ai_model or '(default gpt-4o-mini)'}")
    print(f"       CODE_EXECUTION_ENABLED={settings.code_execution_enabled}  MODE={settings.code_execution_mode}")
    if not key:
        return 1
    if not settings.code_execution_enabled:
        warn("Code execution is OFF -> reports will have no real output. Set CODE_EXECUTION_ENABLED=true")
    elif settings.code_execution_mode == "docker" and shutil.which("docker") is None:
        fail("MODE=docker but the docker command was not found. Set CODE_EXECUTION_MODE=local")
    elif settings.code_execution_mode == "docker" and os.name == "nt":
        warn("MODE=docker on Windows can break under 'uvicorn --reload'. CODE_EXECUTION_MODE=local is safer.")

    print("\n== 2. Real AI call (a few seconds) ==")
    try:
        lab = await OpenAIProvider().generate_solutions(ParsedLab(title="Lab 1", raw_text=LAB_TEXT, tasks=[]))
    except AppError as exc:
        fail(f"{exc.code}: {exc.message}")
        print("       (the full technical cause is printed in the log lines above)")
        return 1
    ok(f"AI returned '{lab.lab_title}' with {len(lab.tasks)} task(s), "
       f"{len(lab.objectives)} objective(s), conclusion: {'yes' if lab.conclusion.strip() else 'no'}")

    print("\n== 3. Running the generated code ==")
    bad = 0
    for task in lab.tasks:
        if not task.code.strip():
            warn(f"{task.id}: no code (conceptual task)")
            continue
        result = await get_executor(task.language).execute(task.code)
        line = (result.stdout or result.stderr).strip().splitlines()
        shown = line[0] if line else "(no output)"
        status = result.status.value
        (ok if status == "success" else fail if status in ("failed", "timeout") else warn)(
            f"{task.id} [{task.language}] -> {status}: {shown[:70]}"
        )
        if status == "unsupported":
            print(f"       reason: {result.stderr.strip()[:140]}")
        bad += status in ("failed", "timeout")
    print("\nDone. If all lines above are [ OK ], generating reports in the UI will work.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
