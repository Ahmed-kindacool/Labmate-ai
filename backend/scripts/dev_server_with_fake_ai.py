"""Runs the real FastAPI app with a FakeAIProvider swapped in for the AI
step, so the whole pipeline (parsing -> AI -> execution -> screenshots ->
DOCX) runs for real and fast, with no OpenAI-compatible API key needed and
no network dependency for that step.

Use this for local iteration on Phases 4-8 without burning API credits,
and to get a fast, deterministic backend for the Playwright E2E suite
(see frontend/e2e/generate-flow.spec.ts and docs/PHASE9_TESTING.md) --
hitting a real AI provider from an E2E test would be slow, occasionally
rate-limited, and non-deterministic in exactly what the "solution" says.

    cd backend
    python scripts/dev_server_with_fake_ai.py

Every other stage is completely real: real PDF/DOCX parsing, real
Docker-sandboxed execution (or a real, honest UNSUPPORTED result if
Docker isn't installed), real Playwright screenshots (or none, if
Chromium isn't installed), real TemplateRegistry + DocxGenerator. Only
the AI call itself is stubbed, returning the fixed GeneratedLab below
regardless of what lab file was uploaded.
"""

import sys
from pathlib import Path

# So `tests/ai_fakes.py` is importable when this is run as a script from
# the backend/ directory, matching how tests/ imports already work.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from ai_fakes import FakeAIProvider  # noqa: E402

from app.ai.service import AIService  # noqa: E402
from app.main import app  # noqa: E402
from app.routes import lab as lab_route  # noqa: E402
from app.schemas.lab import GeneratedLab, GeneratedTaskSolution  # noqa: E402
from app.services.generation_service import GenerationService  # noqa: E402

FAKE_GENERATED_LAB = GeneratedLab(
    lab_title="Lab: Fake-AI Dev Server",
    objectives=["Exercise the real pipeline without a real AI provider."],
    tasks=[
        GeneratedTaskSolution(
            id="task-1",
            description="Print a greeting message.",
            language="python",
            filename="hello.py",
            code="print('Hello from Labmate AI!')",
            explanation="A minimal real task, used to exercise real code execution.",
        )
    ],
    conclusion="This report was generated with a fake AI step and every other stage real.",
)


def main() -> None:
    fake_provider = FakeAIProvider(result=FAKE_GENERATED_LAB)
    lab_route.generation_service = GenerationService(ai_service=AIService(provider=fake_provider))

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
