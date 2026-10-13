# What changed (fix pass)

Run order for a first start on Windows is in README.md → "Running it".

**Why reports weren't generating:** empty `AI_API_KEY` (generic error, nothing logged), code
execution disabled/Docker-only, Chromium-dependent screenshots, no deploy path.

- **AI layer** (`backend/app/ai/`): logged failures + actionable messages (missing key, 401, 404, 429,
  timeout); retries without `response_format` if the provider rejects it; tolerant JSON parsing
  (fences / surrounding text); missing optional fields defaulted; prompt now demands runnable,
  non-interactive code.
- **Execution** (`backend/app/execution/`): new `CODE_EXECUTION_MODE=local` (works on Linux and
  Windows, thread-based so it also works under `uvicorn --reload` on Windows); `docker` mode kept.
  C and C++ compile separately with their own time budget; C is compiled as C.
- **Screenshots** (`backend/app/screenshots/`): Pillow renderer; no Chromium/Playwright needed.
- **Report** (`docx_generator.py`, templates): objectives, per-task explanations, conclusion now
  rendered; Class/Section added to all three templates.
- **Config**: `.env` is found next to `backend/` no matter where uvicorn is started; startup log
  shows AI/execution status; CORS accepts a comma-separated list.
- **Frontend**: download via Blob URL; production build uses relative API URL.
- **Deploy**: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `docs/DEPLOYMENT.md`, CI
  (`.github/workflows/ci.yml`: backend + frontend + Docker smoke test).
- **Tests**: stale template test fixed; +40 tests (local execution incl. isolation, AI parsing,
  report content, screenshots, static serving). Backend 144 pass.
