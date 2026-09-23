# DOCX Generation (Phase 7)

`backend/app/documents/DocxGenerator` is the final stage of the pipeline:

    Lab Parser -> AI Service -> Code Executor -> Screenshot Service
    -> Template Registry (Phase 6) -> DOCX Generator (this phase)

It takes the university's `template.docx` (from `TemplateRegistry`, see
`docs/TEMPLATE_REGISTRY.md`) plus the request's `GeneratedLab`,
`ExecutionResult`s, and screenshots, and fills in every placeholder from
`TEMPLATES_AND_UI.md`, producing the final report as raw `.docx` bytes.

## How each placeholder is filled

| Placeholder             | Filled with                                                             |
|--------------------------|--------------------------------------------------------------------------|
| `{{STUDENT_NAME}}` etc.  | The matching `StudentInfo` field — simple in-place text substitution.   |
| `{{LAB_TITLE}}`, `{{CONCLUSION}}` | The matching `GeneratedLab` field — same simple substitution.  |
| `{{OBJECTIVES}}`         | One bullet paragraph per `GeneratedLab.objectives` entry.                |
| `{{TASKS}}`              | One "Task N: <description>" paragraph per task.                         |
| `{{CODE}}`               | One "Task N — <filename>" heading + a monospace code block per task, in order. Multi-line code keeps every line via real line breaks, not a flattened single line. |
| `{{OUTPUT_SCREENSHOT}}`  | Per task, in this priority order: (1) the real captured screenshot, embedded as an inline image; (2) if no screenshot but the task did run, the raw `stdout` (success) or `stderr` (failed/timeout) text — still real, non-fabricated output; (3) an honest "not supported" note for `UNSUPPORTED`; (4) "No code was executed for this task" if the task never ran at all (e.g. it needed no code). |

This priority order is the direct continuation of `AI_AND_GENERATION.md`'s
anti-fabrication rule ("report the actual failure or omit the
screenshot") — nothing in this list is invented; a task with no real
output gets an honest status note instead of a blank space or made-up
content.

An empty `objectives`/`tasks` list gets a one-line fallback note ("No
objectives were extracted for this lab.") instead of leaving the
placeholder token behind or throwing.

## Why the {{TASKS}} / {{CODE}} / {{OUTPUT_SCREENSHOT}} split, not one repeated block

The template (Phase 6) has one flat section per placeholder, matching
`TEMPLATES_AND_UI.md`'s placeholder list exactly. `DocxGenerator` keeps
that shape — filling each section with every task's content in order —
rather than restructuring the template into one repeating "task card"
(description + code + output together). Restructuring would probably
read better for a multi-task report, but it means changing the Phase 6
template's layout; flagging this as a design question for the team
rather than silently picking a side, per the project's own convention
for cross-cutting decisions.

## Why `download_url` is a data URI

`docs/API_CONTRACT.md` flagged this as an open question: stream the file
directly, or keep `download_url: str` and decide what goes in it later.
Phase 7 resolves it as a base64 **data URI** —
`data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,<...>` —
rather than standing up a new endpoint or in-memory file store:

- The `GenerateSuccessResponse` contract (`download_url: str`) doesn't
  change at all — Dev A's frontend types (`downloadUrl: string` in
  `frontend/src/types/api.ts`) already match this shape with zero
  changes needed.
- The app has no database or persistent storage anywhere else
  (`PROJECT_SPEC.md`'s "No login" MVP scope) — a served-file approach
  would need to invent one (or an in-memory dict keyed by a generated
  ID) just for this, with no real precedent elsewhere in the codebase.
- A data URI is directly usable as an `<a href={downloadUrl} download="lab-report.docx">`
  target in the browser — no extra request, no extra route.

**Trade-off, flagged for the team:** this bloats the JSON response by
the full base64-encoded report size (roughly +33% over the raw `.docx`
size). Fine for a report that's realistically tens of KB to a few MB;
worth revisiting with a dedicated `GET /api/v1/reports/{id}` endpoint if
reports grow large (many screenshots, very long labs) or the response
needs to stay small for other reasons.

## Error handling

Both failure points raise `AppError` with code `REPORT_GENERATION_FAILED`
(per `docs/API_CONTRACT.md`'s error table), reusing the exact same
convention as every earlier phase:

- Opening the template fails (corrupt/unreadable `.docx` on disk) —
  `TemplateRegistry.get_template` itself already raises this for a
  missing file; `DocxGenerator` adds its own catch around `Document(...)`
  for a template file that exists but isn't valid.
- Assembling the final document fails (`document.save(...)` raises).

**A real bug caught during integration, not by inspection:** the Phase 5
test suite's `_FixedScreenshotService` fake returns placeholder bytes
(`b"\x89PNG-fake"`) that were never meant to be a real image — Phase 5
only needed to verify the base64-encoding plumbing, not real image
content. Once Phase 7 wired `DocxGenerator` in, those fake bytes reached
`add_picture` and threw `UnrecognizedImageError`, which would have taken
down report generation over what should be a harmless missing/bad
screenshot. Fixed by catching `UnrecognizedImageError` /
`binascii.Error` around the image-embed step specifically and falling
back to the raw-text output (same as a genuinely missing screenshot) —
covered by its own test (`test_corrupt_screenshot_bytes_fall_back_to_raw_stdout_instead_of_crashing`)
rather than only being implied by the fix.

## Verified

- 20 new tests in `tests/test_docx_generator.py`, all against the real
  checked-in template files (no mocking) — field substitution, every
  university, objectives/tasks/code rendering, all four output-fallback
  branches, real image embedding, and both error paths.
- One real end-to-end check through the actual HTTP route
  (`TestClient` + a fake `AIProvider`, since this sandbox can't reach a
  real OpenAI-compatible API — see `docs/AI_SERVICE.md`): a real POST to
  `/api/v1/labs/generate` returns a `download_url` that decodes to a
  genuine, openable `.docx` with every field filled in correctly.
- Rendered sample reports through LibreOffice (`soffice --headless
  --convert-to pdf`) and inspected the resulting pages visually for all
  three universities, not just asserted on extracted text.
