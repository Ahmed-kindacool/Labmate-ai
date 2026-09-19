# Team Split — 3 Developers (Phase 1 onward)

> **Updated post-migration.** This plan was originally written for a single
> Next.js app. The project has since been migrated to a React (Vite)
> frontend + FastAPI (Python) backend — see `MIGRATION_NOTES.md` at the repo
> root for the full file-by-file mapping. The team split, ownership model,
> and phase sequence below are unchanged; only stack-specific details
> (paths, commands, languages) are updated to match.

Phase 0 is already complete (done by Developer A and Developer B under the
original 2-dev plan). Developer C joins starting here.

## Ownership model

Split by pipeline domain, not by phase:

- **Developer A (Haziq)** — Frontend/UX across every remaining phase.
- **Developer B (Ahmed)** — API/service layer, Lab Parser, AI Service.
  The "understand the lab, generate a solution" half.
- **Developer C (Bilal)** — Code Executor, Screenshot Service, Template Registry,
  DOCX Generator. The "run the code, produce the report" half.

Developer C's first task before Phase 1 work begins: read
`PHASE0_DEV_B_NOTES.md` and `MIGRATION_NOTES.md`, and get **both** halves of
the repo running locally:

```bash
# backend
cd backend
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1        
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Backend-owned pipeline modules (Parser, AI Service, Code Executor, Screenshot
Service, Template Registry, DOCX Generator — i.e. all of B's and C's work)
are now **Python**, living under `backend/app/`, not TypeScript under
`src/lib/`. Frontend-owned work (all of A's work) stays **React + TypeScript**,
now under `frontend/src/` instead of `src/app/` + `src/components/`.

---

## Phase 1 — Frontend UI + API Contract

- **A** — Landing page, student info form, university selector, lab upload,
  Generate button, loading/error states, download/result section. Still a
  stub (`frontend/src/components/lab-form/`, `frontend/src/components/generation/`).
- **B** — `POST /api/v1/labs/generate` (FastAPI): Pydantic request schema,
  validation, file validation, error responses, generation pipeline
  interface (mock response). Already ported — see
  `backend/app/routes/lab.py`, `backend/app/schemas/`.
- **C** — Get ahead on infra since execution/output isn't needed yet:
  ScreenshotService skeleton + a Playwright terminal-render prototype
  (**already done** — `backend/app/screenshots/`, using Playwright's Python
  binding instead of the original JS one); finalize Docker sandbox resource
  limits (no network, timeout, CPU/mem caps) — still outstanding.
- **Together** — connect frontend form to backend (update: now a
  cross-origin request to `http://localhost:8000` instead of a same-origin
  Next.js API route — confirm CORS via `FRONTEND_ORIGIN` in `backend/.env`).

## Phase 2 — Lab File Parsing

- **A** — Drag-and-drop upload, file name display, type/size validation UX,
  upload state, error messages, generation progress UI.
- **B** — `LabParser` architecture (`PdfParser`, `DocxParser`,
  `ParserFactory`) as Python classes in `backend/app/parsing/` (Strategy +
  Factory pattern, same as originally planned — just Python ABCs instead of
  TS interfaces), normalized `ParsedLab` shape (already defined in
  `backend/app/schemas/lab.py`, unused until this phase).
- **C** — `TemplateRegistry` stub for all three universities (placeholder
  docx + logo per template) in `backend/app/templates_registry/`; continue
  sandbox hardening.
- **Together** — test parsing against multiple real lab documents.

## Phase 3 — AI Solution Generation

- **A** — Frontend display for generated solutions: question/solution/code
  layout, expand/collapse, retry UI, error states.
- **B** — `AIService` → `AIProvider` → `OpenAIProvider` adapter as Python
  `ABC`s in `backend/app/ai/` (interface sketch already in
  `docs/AI_AND_GENERATION.md`), `GeneratedLab` structured output validated
  with Pydantic instead of Zod.
- **C** — `CodeExecutor` skeleton (Strategy pattern, `PythonExecutor` stub)
  so Phase 4 has a scaffold to build into — **already done**:
  `backend/app/execution/` defines the `CodeExecutor` interface and a
  `PythonExecutor` that raises "not implemented."
- **Together** — milestone check: lab → questions → AI → structured solutions.

## Phase 4 — Safe Code Execution

- **C (primary)** — `CodeExecutor` (`PythonExecutor`, `CppExecutor`,
  `JavaExecutor`), sandbox security: no network, timeout, CPU/memory limits,
  temp filesystem, cleanup. Still fully outstanding — the Phase 3 stub only
  defines the interface.
- **A** — Frontend execution-result UI: running/success/runtime-error/
  compile-error/timeout states, output display.
- **B** — Supports pipeline wiring between AI output and the executor;
  joins sandbox code review (security-sensitive).
- **Together** — everyone reviews the sandbox implementation.

## Phase 5 — Screenshot Generation

- **C (primary)** — `ScreenshotService`: execution output → HTML renderer →
  Playwright → PNG. **Already implemented** in `backend/app/screenshots/`
  (Python/Playwright port of the original JS version — same terminal-window
  styling, HTML escaping, and 2000-char truncation). Remaining work here is
  wiring it to real `CodeExecutor` output once Phase 4 lands.
- **A** — Report-preview UI (question, code block, terminal-style output).
- **B** — Supports integration between execution results and screenshot
  input; error handling if capture fails.
- **Together** — verify screenshot quality once embedded in the DOCX.

## Phase 6 — University Templates

- **C (primary)** — `TemplateRegistry`: `get_template("air"|"bahria"|"nust")`
  returning `{logo, header, formatting, footer}`, as a Python module in
  `backend/app/templates_registry/`. One shared report structure, not three
  duplicated systems. `University` enum + logo mapping already exist in
  `backend/app/domain/university.py`.
- **A** — University selector, cards, template preview, selected-state UI.
- **B** — Reviews that university identity never leaks into report text;
  aligns template output with the API response shape.
- **Together** — milestone: generate a report with all three templates.

## Phase 7 — DOCX Generation

- **C (primary)** — `DocxGenerator`: `ReportData` → `Template` → `.docx` in
  `backend/app/documents/` (e.g. via `python-docx`, replacing whatever JS
  DOCX library was originally planned), assembling parser + AI + execution +
  screenshot output.
- **A** — Visual design: headings, spacing, typography, code formatting,
  screenshot placement, page breaks, margins, title page, tables.
- **B** — Defines/aligns the `ReportData` shape with what Parser/AI produce.
- **Together** — generate and inspect reports for all three universities.

## Phase 8 — Full Integration

- **A** — Complete frontend flow, UX, loading/error states, responsive
  design, accessibility, download experience, report preview.
- **B** — `GenerationService` end-to-end orchestration
  (`backend/app/services/generation_service.py`), API validation, logging.
- **C** — Temp-file cleanup, execution/screenshot/template failure handling,
  sandbox teardown.
- **Together** — full end-to-end tests, frontend (`localhost:5173`) talking
  to backend (`localhost:8000`) in a realistic dev setup.

## Phase 9 — Testing

- **A** — Frontend (in `frontend/`): form validation, file upload,
  loading/error states, report preview, download flow, responsive UI,
  Playwright user flows. Run via `npm test` / `npm run lint`.
- **B** — Parser + AI (in `backend/`): PDF/DOC parser tests, AI response
  schema validation, API validation tests. Run via `pytest`.
- **C** — Execution + output (in `backend/`): code executor tests, template
  registry tests, DOCX generator tests, execution/screenshot failure
  handling. Also `pytest`; mock the AI provider and skip real sandbox
  execution in CI.
- **Together** — full check, run from each folder separately since it's two
  toolchains now:
  ```bash
  # frontend
  cd frontend && npm run lint && npm run build

  # backend
  cd backend && .venv/bin/pytest
  ```

## Phase 10 — Portfolio Polish

- **A** — Landing page polish, UI consistency, animations, responsive
  design, demo screenshots, branding, README visuals.
- **B** — API documentation (`docs/API_CONTRACT.md` — already updated to the
  FastAPI contract), AI pipeline documentation, parser/AI README sections.
- **C** — Architecture diagram (`docs/ARCHITECTURE.md` — already updated),
  code-execution security documentation, testing documentation,
  template/DOCX pipeline docs.
- **Together** — final GitHub README (overview, problem, solution, features,
  architecture, tech stack — now React/Vite + FastAPI — AI pipeline, code
  execution, templates, screenshots, how to run both services, testing,
  future improvements).

---

## Team rules, adjusted for 3 people

- **Knowledge sharing matters more now.** Whoever builds a component
  explains it to *both* other developers, not just one — the goal is all
  three can talk through the entire architecture in an interview. This
  applies doubly now that the stack is split across two languages: make
  sure A understands the Python side and B/C understand the React side
  well enough to explain the whole system, not just their half.
- **Security-sensitive review is now a three-person job.** The sandbox/
  execution code, the AI integration, and the report-generation logic all
  get reviewed by everyone, not just two.
- Consider one "swap day" mid-project where each dev pairs on a part of the
  pipeline they don't own, so no single person is a point of failure on
  their lane.
