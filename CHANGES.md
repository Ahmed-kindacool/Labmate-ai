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

## Project / documentation labs (e.g. Android Studio assignments)

Problem: an Android lab produced a hollow report ("No code provided" everywhere) because the prompt
only allowed runnable Python/C/C++ and turned the manual's section headings into tasks.

- **Prompt** (`backend/app/ai/prompts.py`): tasks are now the *deliverables* (one per source file the
  lab asks for: activity_main.xml, MainActivity.java, AndroidManifest.xml, ...), complete and using the
  exact IDs/text/values from the document. Any language is allowed; only python/c/cpp are executed.
- **New optional report parts** (`GeneratedLab`): `steps` (what / where / common issue + fix),
  `tables` (e.g. the lifecycle table, pre-filled with the standard documented order), `screenshots`
  (captions), `code_as_text`.
- **DOCX**: source-only code is pasted as real monospaced text (never an image of code); no empty
  "Execution Output" blocks for XML/Java/etc.; numbered Steps section; real tables; dashed empty
  frames with "Figure N: caption" for screenshots you must take yourself; headings keep-with-next;
  Date line added to the Air and Bahria cover pages.
- **Web preview** hides output blocks for source-only tasks.
- Tests: +28 (`tests/test_project_labs.py`). Backend 172 pass.

Not covered: the app cannot compile Android code or take emulator/Logcat screenshots. Build the
generated files in Android Studio, verify the lifecycle table against your own Logcat run, and add your
own screenshots to the frames.

## Parsing
- **DOCX tables are now read** (`backend/app/parsing/docx_parser.py`): paragraphs and tables in document
  order, one table row per line with cells joined by " | ". Before, any table in an uploaded DOCX
  (layout maps, fill-in tables, marking schemes) was silently dropped.
- Images (PDF or DOCX) are still NOT read; only text is sent to the AI.

## Groq / reasoning models ("The AI returned an unexpected response")
Cause: `openai/gpt-oss-120b` is a reasoning model; its hidden thinking tokens share the output budget,
and the request had no explicit budget (Groq's default is ~1k). Big labs came back empty
(`finish_reason=length`; JSON mode failed with `json_validate_failed` + empty `failed_generation`).
- Requests now send `max_completion_tokens` (`AI_MAX_OUTPUT_TOKENS`, default 12000) and
  `reasoning_effort=low` for gpt-oss models (`AI_REASONING_EFFORT` to override).
- Request degrades on provider 400s: full -> without JSON mode -> minimal (`max_tokens` only).
- Real diagnostics: logs `finish_reason`, completion/reasoning tokens; empty/truncated answers and
  HTTP 413 now give accurate messages instead of "unexpected response".
- Tests: +9 (`TestReasoningModelBudget`). Backend 184 pass.

## PDF tables + stricter generation
- **PDF tables are now parsed as tables** (`backend/app/parsing/pdf_parser.py`). Before, table cells were
  flattened into word-wrapped lines that interleaved across columns, so the AI could not tell which value
  belonged to which column. Now each row is one line, cells joined by " | " (an empty cell, such as a
  column to fill in, leaves a trailing "|"); merged-column Word tables are handled; single-cell boxes
  (inline code highlights) are ignored; a header repeated on a continued page is dropped; identifiers split
  mid-token by a narrow cell (`@+id/r` + `ootLayout`) are rejoined. Text outside tables is unchanged.
- **Prompt**: requirement-by-requirement self-check (every named attribute/ID/string must appear, no extra
  structure the document forbids, must build on a current toolchain e.g. android:exported), and tables must
  use the document's exact header text and row labels.
- Tests: +17 (`tests/test_pdf_tables.py`, prompt tests). Backend 196 pass.

## Additional instructions ("anything else you'd like in the report?")
An optional text box on the form. What you type is sent to the AI as the student's own requests, in
addition to what the lab manual asks for.
- **UI**: `components/lab-form/additional-instructions.tsx` (character counter, 5 one-click suggestions:
  Introduction / Viva questions / Comparison table / Discussion / References, backend field errors,
  locked while generating). Sent as the optional multipart field `additional_instructions`.
- **Backend**: validated and cleaned in `app/validation/additional_instructions.py` (control characters
  stripped, max 2000 chars -> field error). Carried on `ParsedLab.additional_instructions` and added to
  the AI prompt as a separate, clearly labelled block *after* the lab text. The lab file is still treated
  as untrusted data; your requests are treated as instructions, but can never override the system rules
  (JSON only, no fabricated output, no changing fonts/layout).
- **Report**: new generic `sections` (title + paragraphs/bullets, `start` or `end` position) for extra
  written parts (Introduction, Discussion, Viva Q&A, References...). Extra code becomes extra tasks and
  extra tables use the existing `tables`.
- Tests: backend +19 (`tests/test_additional_instructions.py`), frontend +7. Backend 215 / frontend 29 pass.
