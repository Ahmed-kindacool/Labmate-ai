# Template Registry

`backend/app/templates_registry/TemplateRegistry` (Phase 6) resolves a
`University` to the on-disk report template it should use. It is the
first stage of the pipeline `PROJECT_SPEC.md` describes for turning a
generated lab into a downloadable `.docx`; Phase 7's `DocxGenerator`
(`backend/app/documents/`, still a stub) is the intended consumer.

## What it returns

```python
from app.domain.university import University
from app.templates_registry import TemplateRegistry

registry = TemplateRegistry()
config = registry.get_template(University.AIR)
# config.university   -> University.AIR
# config.template_path -> .../backend/templates_registry/templates/air/template.docx
# config.logo_path      -> .../backend/templates_registry/templates/air/logo.png
```

`get_template` also accepts a raw string (`"air"`, `"AIR"`, `"Air"` all
resolve the same way), so it can be called directly with a value that
came off a form field without a separate normalization step.

Both paths are verified with `Path.is_file()` before the call returns.
Phase 7 can open them directly — it never needs to re-check existence or
guess a path shape.

## On-disk layout

```text
backend/templates_registry/templates/
├── air/
│   ├── template.docx
│   └── logo.png
├── bahria/
│   ├── template.docx
│   └── logo.png
└── nust/
    ├── template.docx
    └── logo.png
```

This mirrors `TEMPLATES_AND_UI.md`'s spec exactly. Paths are resolved
relative to `templates_registry/__init__.py`'s own location
(`Path(__file__).resolve()...`), not the process's current working
directory — the Phase 2 stub this replaced used a hardcoded relative
string (`"backend/templates_registry/templates/..."`) that only resolved
correctly if the server happened to be launched from the repo root.

## The three templates

All three `template.docx` files share the same layout and formatting.
The only difference between them is the embedded logo in the header —
per `TEMPLATES_AND_UI.md`'s "Critical requirement," the university name
is never inserted into the document as text; selecting a university only
ever selects which template/logo pair `get_template` returns.

Each template contains these placeholders, in the body (not the header):

```text
{{STUDENT_NAME}}       {{ROLL_NUMBER}}       {{CLASS_SECTION}}
{{INSTRUCTOR_NAME}}    {{COURSE}}            {{LAB_TITLE}}
{{OBJECTIVES}}         {{TASKS}}             {{CODE}}
{{OUTPUT_SCREENSHOT}}  {{CONCLUSION}}
```

`{{OUTPUT_SCREENSHOT}}` is a text placeholder, not an actual embedded
image — Phase 7 is expected to replace that paragraph with the real PNG
that `app/screenshots/` already produces per task (see
`docs/Screenshots.md`), the same way it replaces every other placeholder
with real content.

The logo itself is already embedded as an image (not a placeholder) in
each template's header, sized to fit next to the "Lab Report" title —
Phase 7 doesn't need to insert it, only leave it alone.

## Error handling

Two things can go wrong, and both raise `AppError` with code
`REPORT_GENERATION_FAILED` (there's no more specific `AppErrorCode` for a
template-lookup failure — see `app/schemas/generate.py`) rather than a
bare `ValueError` or an unhandled 500:

- **Unrecognized university** — a string that doesn't match any
  `University` member. In practice this shouldn't happen by the time
  `get_template` is called: `StudentInfo.university` is already typed as
  `University`, so an invalid value is rejected earlier, at request
  validation, as `INVALID_INPUT`. The check in `get_template` exists for
  defensive/direct-call cases (tests, scripts, future call sites) rather
  than as the primary validation path.
- **Missing template or logo file** — the university is valid but its
  `template.docx` or `logo.png` isn't on disk. This is the failure mode
  the Phase 2 stub had no way to detect at all; it would have returned a
  path string pointing at nothing and let the failure surface later,
  inside Phase 7.

## Regenerating a template

If a template needs layout changes, the cleanest path is regenerating it
with `python-docx` rather than hand-editing the `.docx` in Word/LibreOffice
and re-exporting — hand edits are hard to keep byte-identical across all
three universities, and "same layout, different logo" is the one
constraint `TEMPLATES_AND_UI.md` is strict about. Keep the placeholder
tokens exactly as listed above (Phase 7 will likely do a literal
`{{TOKEN}}` find-and-replace across paragraph runs) and re-embed the
correct logo from `frontend/public/logos/<university>.png` in the header.
