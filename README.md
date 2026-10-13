# Labmate AI

Upload a university lab (PDF, DOC, or DOCX). Labmate AI reads it,
generates real code and explanations for each task, actually **runs**
that code in a sandboxed environment, and returns a formatted `.docx`
report — with your university's real branding — containing the
original questions, the generated solutions, and genuine execution
output. Not a mockup of what the code would print: what it actually
printed.

![Upload, generate, and download flow](docs/assets/screenshots/flow-demo.png)

*Real screenshots of the running app (via Playwright, against the real
backend) — not mockups. Also supports dark mode and is responsive down to
mobile:*

<p>
  <img src="docs/assets/screenshots/02-landing-dark.png" alt="Dark mode" width="420">
  <img src="docs/assets/screenshots/06-mobile-success.png" alt="Mobile view" width="160">
</p>

## Why this exists

Writing up a lab report is repetitive: retype the questions, write and
test the code, take a screenshot of the output, paste everything into a
university-branded template. Labmate AI automates all of it except the
one part that should stay human — actually understanding the material.

## How it works

1. **Upload** a lab file and pick your university (Air University,
   Bahria University, or NUST).
2. **AI generates a solution** — objectives, task descriptions, code,
   and a short explanation per task. The AI never claims code was run;
   it only ever describes what the code is intended to do
   (`docs/AI_AND_GENERATION.md`).
3. **Code actually executes**, for real (Python, C, C++), in a resource-
   limited sandbox with a hard timeout (`docs/DEPLOYMENT.md`,
   `docs/CODE_EXECUTION_SECURITY.md`).
4. **Real output gets captured** as a terminal-style screenshot.
5. **A `.docx` report is assembled** from your university's real
   template — logo, layout, every placeholder filled with genuine
   content, never a fabricated one (`docs/DOCX_GENERATION.md`).

If any step can't produce something real — code execution disabled,
Docker unavailable, an unsupported language, a screenshot that failed to
render — the report says so honestly instead of inventing output. See
"Anti-fabrication rule" in `docs/AI_AND_GENERATION.md`.

## Architecture

```mermaid
flowchart TD
    UI["React (Vite) UI"] -->|multipart/form-data| Route["POST /api/v1/labs/generate"]
    Route --> GS["GenerationService"]
    GS --> Parser["Lab Parser"]
    GS --> AI["AI Service"]
    GS --> Exec["Code Executor (Docker sandbox)"]
    GS --> Shots["Screenshot Service"]
    GS --> Templates["Template Registry"]
    GS --> Docx["DOCX Generator"]
    Templates --> Docx
    Docx --> Response["download_url (base64 data URI)"]
```

One backend service, no microservices, no database, no auth — a
deliberately small modular monolith. Full breakdown, folder structure,
and design-pattern rationale in `docs/ARCHITECTURE.md`.

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 19 + Vite, TypeScript, Tailwind, shadcn/ui |
| Backend | FastAPI (Python), Pydantic |
| AI | OpenAI-compatible `/chat/completions` API — works with OpenAI itself or a free-tier provider (Groq, Gemini, OpenRouter) via one env var, no code changes (`docs/AI_SERVICE.md`) |
| Code execution | Python, C, C++ — in-container locked-down subprocess (`local`, default in the Docker image) or one Docker container per run (`docker`) |
| Screenshots | Pillow (terminal-style PNGs; no browser needed) |
| Reports | python-docx |
| Testing | pytest + pytest-cov (backend), Vitest + Playwright (frontend) |

## Running it

**Docker (recommended, and the deployable artifact):**

```bash
docker build -t labmate .
docker run -p 8000:8000 -e AI_API_KEY=sk-... labmate     # open http://localhost:8000
```

One container serves the UI and the API, with real code execution and
screenshots working out of the box. Details, free AI providers, and the
sandbox's security model: `docs/DEPLOYMENT.md`.

**Local development (two processes):**

```bash
cd backend && pip install -r requirements.txt
cp .env.example .env     # set AI_API_KEY; for real output also set
                         # CODE_EXECUTION_ENABLED=true and CODE_EXECUTION_MODE=local
uvicorn app.main:app --reload                 # localhost:8000

cd frontend && npm install && npm run dev     # localhost:5173
```

Open `http://localhost:5173` — **not** `127.0.0.1` (CORS origin; see
`docs/PHASE8_INTEGRATION.md`). No AI key handy?
`python scripts/dev_server_with_fake_ai.py` runs the whole pipeline with a
fixed fake AI answer.

The server logs its configuration on startup (`AI configured: yes | code
execution: enabled (local)`), and AI failures are logged with their real cause.

## Testing

```bash
cd backend && pytest --cov=app --cov-report=term-missing
cd frontend && npm run lint && npm run build && npx vitest run
cd frontend && npx playwright test   # real browser, real backend
```

Full write-up of what's covered and how (including genuinely unmocked
Playwright screenshot tests) in `docs/PHASE9_TESTING.md`.

## Documentation

| Doc | Covers |
|---|---|
| `docs/PROJECT_SPEC.md` | Original scope and requirements |
| `docs/ARCHITECTURE.md` | Full architecture, folder structure, design patterns |
| `docs/API_CONTRACT.md` | The real `POST /api/v1/labs/generate` request/response shape |
| `docs/AI_AND_GENERATION.md` | The AI pipeline, prompt rules, anti-fabrication design |
| `docs/AI_SERVICE.md` | Configuring an AI provider, incl. free-tier options |
| `docs/CODE_EXECUTION_SECURITY.md` | The Docker sandboxing threat model and controls |
| `docs/Screenshots.md` | Real-output terminal screenshot rendering |
| `docs/TEMPLATE_REGISTRY.md` | University template/logo resolution |
| `docs/DOCX_GENERATION.md` | Final report assembly |
| `docs/PHASE8_INTEGRATION.md` | Frontend-backend wiring, a real CORS gotcha found live |
| `docs/PHASE9_TESTING.md` | Test coverage, what's real vs. mocked, and why |
| `docs/DEPLOYMENT.md` | System dependencies (antiword, Docker, Playwright) |

## Future improvements

- **Real per-step generation progress.** The backend is currently one
  request/response; the frontend estimates progress locally rather than
  the backend streaming real per-stage signals. SSE or polling would be
  the real fix.
- **CI** (`.github/workflows/ci.yml`) runs backend tests, frontend lint/build/unit
  tests, and a Docker build + smoke test. The Playwright E2E suite is not in CI yet.
- **Legacy `.doc` support** (via `antiword`) is the only parser with an
  external system dependency, and its real success path has never been
  exercised in any environment this project has been developed in —
  worth deciding if it's worth keeping.
- **Rate limiting** on the code-execution path — each execution is
  individually sandboxed and bounded, but nothing yet throttles how many
  run concurrently.
