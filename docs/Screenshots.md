# Screenshots (Phase 5)

Renders real execution output as terminal-style PNG screenshots, for
eventual embedding in the DOCX report (Phase 7). Lives in
`backend/app/screenshots/`.

## ⚠️ Fixed before this phase started: a broken merge on `app/execution/__init__.py`

Before any Phase 5 work, `origin/main`'s `backend/app/execution/__init__.py`
contained **unresolved git merge conflict markers**
(`<<<<<<<`/`=======`/`>>>>>>>`) — invalid Python, so the entire backend
failed to import. This happened because Dev C's `docker`-SDK-based
`PythonExecutor` (a different, competing implementation of the same file
this project already has as
`app/execution/{executor,factory,python_executor,unsupported_executor}.py`)
was merged without resolving the conflict against that existing work.

**Fixed** by keeping the existing Strategy-pattern implementation (already
tested, and the only one satisfying `PROJECT_SPEC.md` §4's disable-rather-
than-unsafe requirement and the execution timeout) and removing the
conflict markers plus the competing code. Verified live: the app now
imports and boots cleanly, and the full test suite (55 tests before this
phase's additions) passes.

**Process note for the team:** this should have been caught before pushing
— `python -c "import app.main"` (or just running the test suite) fails
immediately on a file with conflict markers in it. Worth agreeing on
running that locally before any push, or adding it as a CI check.

**Side effect worth knowing about:** `frontend/src/components/generation/execution-output.tsx`
was written against the *other* side of that conflict — Dev C's
`{output, success, error}` shape — not the `{status, stdout, stderr,
exit_code}` shape that's actually in `app/schemas/lab.py` and is what the
API has returned since Phase 4. That component needs reconciling with the
real contract; see "Open items" below for a suggested mapping.

## Architecture

```text
GenerationService
      │
      ▼
 ScreenshotService.capture_many(execution_results)
      │
      ▼
 render_terminal_html(text)  →  one shared Chromium instance  →  PNG bytes
```

| File | Responsibility |
|---|---|
| `app/screenshots/terminal_renderer.py` | Builds the terminal HTML/CSS — extracted from Dev C's original function, byte-for-byte |
| `app/screenshots/service.py` | `ScreenshotService` — batches all of a report's screenshots under one browser |
| `app/screenshots/__init__.py` | Re-exports `ScreenshotService`, plus the original single-shot `generate_terminal_screenshot()` for standalone use |

**Why one browser per report, not one per task:** launching Chromium has a
real, fixed startup cost. `generate_terminal_screenshot()` (Dev C's
original, still available) launches and tears down a browser per call —
fine for one screenshot, wasteful for a lab with several executed tasks.
`ScreenshotService` launches once and reuses that browser (a fresh
context per screenshot, for isolation) across every task in the report.

**Markup is shared, not duplicated:** Dev A's `task-report-preview.tsx`
frontend component explicitly mirrors this HTML/CSS token-for-token so the
live preview matches the real screenshot. `terminal_renderer.py` is the
one place that markup lives on the backend — don't restyle it without
updating that component too.

## Which results get a screenshot

Per the anti-fabrication rule in `AI_AND_GENERATION.md` ("report the
actual failure or omit the screenshot"):

| `ExecutionResult.status` | Screenshotted? | Source text |
|---|---|---|
| `success` | Yes | `stdout` |
| `failed` | Yes | `stderr` (the real error) |
| `timeout` | Yes | `stderr` (the real timeout message) |
| `unsupported` | No | — nothing genuinely ran, so there's no real output to show |

## Data contract

`GenerateSuccessResponse.screenshots: Optional[dict[str, str]]` — task ID
→ base64-encoded PNG, one entry per task that got a screenshot.

**This is not currently consumed by the live frontend preview.**
`report-preview.tsx` re-renders the terminal from raw `stdout`/`stderr`
text client-side (using the same mirrored markup) rather than displaying
this image — it's faster and needs no round trip. This field exists for
Phase 7 (embedding the actual PNG in the DOCX) and for manual
verification; nothing here blocks the frontend.

## Failure handling

A screenshot problem (Chromium missing, a render failure, anything)
degrades the response to `screenshots: None` rather than failing the
whole request — `GenerationService._capture_screenshots()` catches it.
The report is still useful with real generated code and execution output
even without images.

## Testing

```
cd backend
python -m pytest tests/test_screenshots.py tests/test_generation_service_phase5.py -v
```

- `TestRenderTerminalHtml` — HTML escaping (XSS-safety for arbitrary
  program output), truncation at 2000 chars.
- `TestScreenshotService` — capturable-status filtering, stdout vs stderr
  selection, and confirms exactly one browser launch regardless of task
  count — all with Playwright's `async_playwright`/`Browser`/`Page`
  mocked.
- `TestGenerationServiceScreenshots` — the graceful-degrade behavior when
  screenshotting raises, and base64 round-tripping.

**Not covered: an actual Chromium screenshot.** This sandbox can't
download Playwright's Chromium binary (network egress restricted to an
allowlist that doesn't include `cdn.playwright.dev`), so this is verified
with Playwright's API mocked, the same technique used for Docker (Phase 4)
and the OpenAI SDK (Phase 3). Whoever has Chromium installed locally
should run one real end-to-end check — `CODE_EXECUTION_ENABLED=true` +
Docker + Chromium, submit a lab, confirm a real PNG comes back — before
relying on this in production.

## Open items for the team

1. **Reconcile `execution-output.tsx`** with the real contract. Suggested
   mapping from `{status, stdout, stderr, exit_code}` to what that
   component currently expects:
   - `success` → `status === "success"`
   - `output` → `status === "success" ? stdout : stderr`
   - `error` → switch on `status` directly (`"timeout"` → "Timed out",
     `"failed"` → "Execution failed", etc.) instead of the current
     keyword-matching on a freeform string — the enum makes
     `categorizeError()`'s string-sniffing unnecessary.
2. Same snake_case reconciliation as Phases 3/4 still open: `labTitle` →
   `lab_title`, `exitCode` → `exit_code`.
3. Agree on a pre-push check (test suite run, or just `import app.main`)
   to catch broken merges like this phase's before they land on `main`.
