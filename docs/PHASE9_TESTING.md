# Phase 9: Testing

A broader pass across the whole team's work, per `docs/TEAM_SPLIT_PHASE1_ONWARD.md`'s
Phase 9 breakdown. The single biggest gap: **the frontend had zero tests
of any kind** and `npm run lint` failed outright (no ESLint config file
existed at all). The backend already had solid coverage from Phases 2-8;
this phase used `pytest-cov` to find its real remaining weak spots
instead of assuming it was complete.

## Frontend: from nothing to a real suite

- **Vitest + React Testing Library**, configured in `vite.config.ts`
  (`test:` block) and `src/test/setup.ts`. Deliberately kept `globals`
  off — every test file imports `describe`/`it`/`expect`/`vi` explicitly
  from `"vitest"` rather than relying on injected globals.
- **`eslint.config.js`** (new) — standard Vite + React + TS flat config.
  `npm run lint` now actually runs: 0 errors, 1 pre-existing warning
  (shadcn's own `button.tsx` exporting a helper alongside the component,
  which is the normal shadcn pattern, not a bug).
- **23 unit tests** across `generate-api.ts`, `ExecutionOutput`,
  `StudentInfoForm`, and a full `App.tsx` integration test (mocked
  `fetch`, real component tree) covering the success path, a real
  backend error response, a network failure, and the reset flow.
- **A real bug caught while writing the App-level test, not by
  inspection**: "Start over" never actually reset `studentInfo` — the
  form kept showing whatever was typed before. Fixed in `App.tsx`; the
  test (`"Start over after an error clears the form back to its initial
  state"`) now guards it.
- **A real environment gotcha, not a bug**: `@testing-library/react`'s
  auto-cleanup between tests only registers itself if it finds a
  *global* `afterEach` at import time — which never happens here, since
  `globals` is off by design. Without an explicit `cleanup()` in
  `src/test/setup.ts`, every test's rendered DOM silently piled up across
  the rest of that file, causing `getByRole` to find duplicate/stale
  elements from earlier tests. Fixed once, centrally, in `setup.ts`.
- **jsdom doesn't implement `matchMedia` at all** (a real browser does)
  — `use-theme.ts` reads it on every mount. A minimal stub in
  `setup.ts` was enough (only `.matches` is ever read, no listener API).

## A committed Playwright E2E suite (`frontend/e2e/`)

Formalizes what Phase 8's write-up described as an ad-hoc verification
script into a real, repeatable, committed suite: form validation,
file-upload state, a full real submit-to-download round trip, and the
reset flow — driven against the actual running app in a real browser,
no mocked `fetch` anywhere.

**`backend/scripts/dev_server_with_fake_ai.py`** (new) is what makes the
"submit and get a real download" E2E test both fast and deterministic:
it runs the real FastAPI app with only the AI call swapped for the same
`FakeAIProvider` test double `tests/ai_fakes.py` already uses. Every
other stage — parsing, execution (or a real, honest `UNSUPPORTED` if
Docker isn't installed), screenshots, `TemplateRegistry`, `DocxGenerator`
— runs completely for real. This is also just a genuinely useful dev
tool going forward: local iteration on Phases 4-8 without burning API
credits or waiting on a real AI response.

`playwright.config.ts` reads an optional `PLAYWRIGHT_CHROMIUM_PATH` env
var for pointing at a pre-installed Chromium binary in a sandbox that
can't reach Playwright's own CDN (see below) — **on a normal dev
machine, ignore this entirely**: just run `npx playwright install
chromium` once, and leave the env var unset.

## Backend: closing real gaps found by `pytest-cov`, not guessed at

Coverage before this phase: 94%. The two largest real gaps:

- **`app/parsing/doc_parser.py` — 39%.** The legacy `.doc` parser's real
  success path (shelling out to `antiword`) has never actually run in
  any environment this project has been developed in, since `antiword`
  isn't installed. Still true here — left as a known gap, same as it's
  always been (see the "worth keeping?" open item in
  `PROJECT_HANDOFF.md`), rather than adding another test that only
  proves it skips itself.
- **`app/screenshots/__init__.py` / `service.py` — 33%.** Every existing
  screenshot test mocked Playwright entirely, for the same reason as the
  `.doc` parser: this project's sandboxes generally can't reach
  Playwright's CDN to download a browser. **This one *was* closeable.**
  See below.

### Real, unmocked Playwright tests are now possible

Phase 8 found that this particular sandbox happens to have a real
Chromium (`headless_shell`) pre-installed for unrelated reasons, at a
path Playwright's own installer doesn't use. Phase 8 used it with an
explicit `executable_path` override to verify the frontend visually.
This phase does the same for the backend's own screenshot code — but
`ScreenshotService`/`generate_terminal_screenshot` call
`chromium.launch()` with **no arguments** (correctly — production code
has no business hardcoding a sandbox-specific path), so making this work
without touching production code needed a test-only shim.

The first attempt (wrap `playwright.chromium` in a proxy object) failed
immediately: `Playwright.chromium` is a read-only property, not a plain
attribute — can't be reassigned. The working approach, in
`tests/conftest.py`'s `real_chromium_playwright` fixture: monkeypatch
`BrowserType.launch` **at the class level**, injecting
`executable_path` only when the caller didn't supply one. Every call
after that — the real playwright instance, real browser, real context,
real page, real PNG bytes — is untouched, genuinely real Playwright.

Gated behind a `SANDBOX_CHROMIUM_PATH` env var; the fixture `skip`s
(doesn't fail) when it's unset or the path doesn't exist, so this never
breaks CI or another contributor's machine — it only activates where
it's explicitly opted into:

```bash
SANDBOX_CHROMIUM_PATH=/path/to/chromium/binary pytest
```

4 new tests in `tests/test_screenshots.py`
(`TestWithRealUnmockedChromium`) check real PNG file signatures
(`\x89PNG\r\n\x1a\n`), that multiple tasks in one report produce
genuinely different images (not the same bytes copy-pasted), and that a
failed task's real stderr text still renders to a real, non-trivial
image. `app/screenshots/__init__.py` and `service.py` are now both 100%
covered.

### Five smaller real gaps closed (`tests/test_hardening.py`)

Found the same way — real, untested lines, not filled in for coverage's
own sake:

| Gap | Why it mattered |
|---|---|
| `/api/v1/health` had no test at all | Trivial, but genuinely unverified |
| Whitespace-only field value (`"   "`) | Passes a naive `if not value` check; must still fail the same as empty — this is what `not_blank`'s `.strip()` exists for, and nothing exercised that branch |
| Omitting the `lab_file` form field entirely | Different code path from an unsupported/oversized/unreadable file; never tested |
| A genuinely unhandled exception (not `AppError`) | `app/core/errors.py`'s promise to "never leak stack traces, secrets, or internal paths" (`PROJECT_SPEC.md` §7) had never actually been exercised against a real, arbitrary exception |
| A task with blank/no code | `GenerationService._execute_tasks`'s `continue` (skip codeless tasks, never send them to the executor) had no test |

**A real Starlette/TestClient quirk surfaced while writing the
unhandled-exception test:** `TestClient` defaults to
`raise_server_exceptions=True`, which re-raises into the test instead of
invoking the registered catch-all `Exception` handler — a deliberate
debugging aid, but it meant the test initially failed by *crashing with
the real traceback* rather than checking a response. A real deployed
server (`uvicorn`) doesn't have this bypass. Fixed by using
`TestClient(app, raise_server_exceptions=False)` for that one test, to
exercise the actual production code path.

One more gap closed in `test_docx_generator.py`: a template missing a
placeholder entirely (a legitimate future state, per
`docs/TEMPLATE_REGISTRY.md` — not every section is guaranteed to survive
a template edit) had never been tested; each `_fill_*` method's `if
target is None: return` guard exists for exactly this, untested until
now.

**Backend coverage: 94% → 97%** (109 passed, 1 skipped — the `.doc`
parser test, same as always). Remaining gaps are narrow, low-value
defensive branches (a `document.save()` I/O failure, a `docker kill`
race condition already handled by a `try/except ProcessLookupError`) —
diminishing returns past this point, left as-is.

## Verified together

```bash
cd backend && pytest --cov=app --cov-report=term-missing   # 109 passed, 1 skipped, 97%
cd frontend && npm run lint && npm run build && npx vitest run   # 0 errors, build OK, 23 passed
cd frontend && npx playwright test   # 4 passed, real browser, real backend
```

## Known gaps, still open

- `.doc` parsing's real success path — blocked on `antiword` not being
  installed in any environment this has been developed in. Same open
  question as before: is legacy `.doc` support worth keeping at all?
- No CI workflow runs any of this automatically yet (`.github/workflows/`
  doesn't exist) — the "no pre-push safety check" item from
  `PROJECT_HANDOFF.md` is still open. This phase makes the check
  commands real and fast; wiring them into CI is a natural next step,
  probably folded into Phase 10.
