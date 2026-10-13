# Deployment

## TL;DR — one container

```bash
docker build -t labmate .
docker run -p 8000:8000 -e AI_API_KEY=sk-... labmate        # → http://localhost:8000
# or: AI_API_KEY=sk-... docker compose up --build
```

The image builds the React app and serves it from FastAPI, so the UI and API
share one origin: **no CORS and no API URL to configure**. It also bundles
everything a report needs: `gcc`/`g++` (C and C++ tasks), `antiword` (`.doc`
uploads) and a monospace font (code/output screenshots).

Works on any host that runs a Dockerfile (Render, Railway, Fly.io, a VPS,
Cloud Run). Set `AI_API_KEY` (and optionally `AI_MODEL`, `AI_BASE_URL`) as
runtime environment variables — never in the image. The container listens on
`$PORT` (default 8000). Health check: `GET /api/v1/health`.

Free OpenAI-compatible providers work without code changes — see
`docs/AI_SERVICE.md` (e.g. Groq: `AI_BASE_URL=https://api.groq.com/openai/v1`,
`AI_MODEL=llama-3.3-70b-versatile`).

## What a working deployment looks like

On startup the log prints one line that tells you immediately if anything is
misconfigured:

```
AI configured: yes | code execution: enabled (local)
Serving frontend from /app/frontend_dist
```

`AI configured: NO` → set `AI_API_KEY`. AI failures are logged server-side with
the real cause (bad key, wrong model name, rate limit, unusable output) while
users see a short actionable message.

## Code execution

Reports contain **real** output only if code execution is on. Two backends:

| `CODE_EXECUTION_MODE` | Use when | Isolation |
|---|---|---|
| `local` (Docker image default) | The app runs in its own disposable container (almost every PaaS). | Child process: empty env, own working dir, CPU/memory/file/fd limits, process-group kill on timeout, no stdin, output capped, **runs as `nobody` (uid 65534) when the server is root** so it can't read the server's env/secrets via `/proc`. **No network namespace.** |
| `docker` | You control a host with Docker and can give the app the socket. | One container per run: `--network none`, read-only FS, CPU/memory/pid limits. Strongest isolation. |

Notes for `local` mode:

- Keep the default root user in the image (the drop to `nobody` needs it) and
  don't put secrets in files readable by other users.
- The code **can** make outbound network calls from the container. If that
  matters, deny egress at the platform/network level, or use `docker` mode.
- The sandbox container should hold no data you can't afford to expose; the
  student code is AI-generated from an uploaded (untrusted) document.
- Limits: `CODE_EXECUTION_TIMEOUT_SECONDS` (default 10, per run) and
  `CODE_COMPILE_TIMEOUT_SECONDS` (default 30, C/C++ only).

If execution is disabled/unavailable the report says so honestly ("Code
execution is currently disabled…") instead of inventing output.

## Local development (no Docker)

```bash
# backend
cd backend && pip install -r requirements.txt
cp .env.example .env            # set AI_API_KEY; for real output also:
                                #   CODE_EXECUTION_ENABLED=true  CODE_EXECUTION_MODE=local
uvicorn app.main:app --reload

# frontend (another terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

No AI key? `python scripts/dev_server_with_fake_ai.py` runs the real pipeline
with a canned AI answer.

Optional system packages: `g++`/`gcc` for C/C++ execution, `antiword` for `.doc`
uploads, and a font such as DejaVu Sans Mono for nicer screenshots (Pillow falls
back to a built-in font). **Screenshots no longer need Chromium or Playwright.**

## Operational notes

- A generation is one long request (AI call + execution). If a proxy in front
  of the app times out at 30–60 s, raise its timeout; large labs can take
  longer.
- Rate limiting is not built in. If the site is public, add it at the platform
  level — every request spends AI tokens and CPU.
- `MAX_UPLOAD_SIZE_MB` caps uploads (default 10).
