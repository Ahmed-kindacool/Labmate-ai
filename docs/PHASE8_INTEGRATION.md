# Phase 8: Full Integration

The frontend now calls the real backend end to end: student info form ->
university selector -> lab upload -> `POST /api/v1/labs/generate` -> real
progress -> download link + report preview, or a real error banner.
Previously, `App.tsx` never made a network request at all — it drove
`GenerationProgress` off a local `setInterval`, and the student-info
form/university-selector components existed but weren't mounted anywhere.

## What changed

- **`StudentInfoForm`** (new) — the missing piece: name, roll number,
  class/section, instructor, course, wired to the existing
  `UniversitySelector`. Mounted in `App.tsx` alongside `LabFileUpload`.
- **`lib/generate-api.ts`** (new) — the actual `fetch` to
  `POST /api/v1/labs/generate`, building the real multipart form and
  distinguishing "no server response at all" (`GenerateRequestError`,
  shown via `GenerationError`'s existing network-failure copy) from a
  real, backend-authored `{status: "error", ...}` response.
- **Every flagged frontend/backend naming mismatch, resolved by renaming
  the frontend to match the backend** (not a translation layer — see
  each type file's comment for why):
  - `GeneratedLab.labTitle` -> `lab_title`
  - `ExecutionResult.exitCode` -> `exit_code`
  - `GenerateSuccessResponse.downloadUrl` -> `download_url`
  - `StudentInfo`'s `rollNumber`/`classSection`/`instructorName` -> `roll_number`/`class_section`/`instructor_name`
- **`execution-output.tsx`, `task-report-preview.tsx`, `report-preview.tsx`
  rewired to the real `ExecutionResult` shape** (`status`/`stdout`/`stderr`/`exit_code`).
  These were built against a competing `{output, success, error}` shape
  from a backend implementation that lost a merge conflict and was
  removed in Phase 5 (see `docs/DOCX_GENERATION.md` /
  `PROJECT_HANDOFF.md`) — this was the last place that dead shape
  still existed anywhere in the codebase.
- **`types/api.ts`'s `GenerateSuccessResponse`** now actually includes
  `generated_lab`, `execution_results`, and `screenshots` — fields the
  backend has shipped since Phases 3-5 but the frontend type never
  declared, so nothing could render them.
- **`frontend/src/vite-env.d.ts`** (new) — was missing entirely, so
  `import.meta.env` had no types. Standard Vite scaffolding file that
  should have existed from Phase 0.

## A design note carried over from Phase 4/5, unchanged in Phase 8

`docs/DOCX_GENERATION.md` already noted this, worth repeating here: the
live frontend preview renders the terminal from `ExecutionResult.stdout`/
`stderr` text client-side (`TaskReportPreview`'s own `TerminalWindow`,
which mirrors the backend screenshot renderer's HTML/CSS token-for-token)
rather than displaying the actual screenshot PNG. The screenshot image is
only for embedding into the generated `.docx`. This is a deliberate,
pre-existing design choice, not a Phase 8 gap.

## Real bug found during live verification: CORS origin mismatch

Testing against `http://127.0.0.1:5173` instead of `http://localhost:5173`
produced a genuinely confusing failure: the backend logged a real `200
OK` for the `POST`, but the browser's `fetch()` still rejected, and the
UI showed "Could not reach the server" — because `CORSMiddleware` in
`app/main.py` only allows the exact origin in `settings.frontend_origin`
(`http://localhost:5173` by default), and browsers treat `localhost` and
`127.0.0.1` as different origins. The request reaches the server and
executes fully either way — only the browser's ability to *read* the
response is blocked.

**Not a code bug** — `http://localhost:5173` (Vite's own default/logged
URL) matches the default config exactly, and re-testing against it
worked immediately. Documenting it here because it's a real trap for
whoever runs `npm run dev` + `uvicorn` next and happens to open
`127.0.0.1` out of habit: **always use `http://localhost:5173`**, or set
`FRONTEND_ORIGIN` in the backend's `.env` to match whichever host you
actually use.

## Verified for real

- `tsc -b --noEmit` and `npm run build` both clean.
- A real Chromium (`headless_shell`, pre-installed in this sandbox at
  `/opt/pw-browsers/` — see "Aside" below) drove the actual running app:
  filled the real form, uploaded a real PDF, clicked the real button,
  and got back a real, decoded, valid `.docx` via the real download
  link — rendered and visually inspected (correct university logo,
  correct student fields, real code, an honest "execution not
  supported" note since this sandbox has no Docker, matching Phase 4's
  tested degrade-gracefully behavior exactly).
- Ran against a real backend process with a `FakeAIProvider` swapped in
  (same test double `tests/ai_fakes.py` already uses) rather than a
  mocked HTTP layer, since this sandbox's network egress still can't
  reach a real OpenAI-compatible API — see `docs/AI_SERVICE.md`.

### Aside: a real Chromium is available in this sandbox

Phase 5 flagged Playwright/Chromium as untestable here ("this sandbox
can't download Playwright's Chromium binary"). That's still true for
*downloading* one at request time, but a real `headless_shell` build
already exists at `/opt/pw-browsers/chromium_headless_shell-1194/`. It's
what made the live browser verification above possible. It's worth
someone checking whether `ScreenshotService` itself
(`backend/app/screenshots/`) can point at this same binary via
Playwright's `executable_path` — that would upgrade Phase 5's "known
limitation, tested with the API mocked" to a real, unmocked smoke test,
without needing network access to Playwright's CDN at all.

## Known gaps, flagged rather than fixed here

- **No real progress signal.** The backend is one request/response; the
  5-step `GenerationProgress` UI advances on a capped local timer
  (never claims completion before the real response arrives) rather
  than real per-stage signals. SSE or polling would be the real fix,
  and is a reasonable Phase 9+ item.
- **ESLint has no config file at all** (`eslint.config.js` missing) —
  `npm run lint` fails outright, unrelated to this phase. Not fixed
  here since it's a separate, pre-existing gap; flagging it since
  Phase 8 is the first time anyone would have run it against real
  frontend logic changes.
- **Field-level validation error rendering** (`StudentInfoForm`'s
  `fieldErrors` prop, fed from `GenerateErrorResponse.field_errors`) is
  exercised by the type system and the existing backend contract tests,
  but not by a live browser test in this phase — the UI's own
  client-side validation (`isStudentInfoComplete`) prevents an empty
  submission before it happens, and provoking a real `INVALID_INPUT`
  through the live UI wasn't attempted, unlike everything else above.
