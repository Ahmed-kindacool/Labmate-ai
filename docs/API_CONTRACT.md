# API Contract — POST /api/v1/labs/generate

> **Updated during migration.** Path and field names changed from the
> original Next.js version (`POST /api/generate`, camelCase fields) to
> match the FastAPI backend. See `../MIGRATION_NOTES.md`.

## Request

`multipart/form-data` with these fields:

| Field             | Type   | Required | Notes                                |
|-------------------|--------|----------|----------------------------------------|
| `name`            | string | yes      |                                        |
| `roll_number`     | string | yes      |                                        |
| `university`      | string | yes      | one of `"air" \| "bahria" \| "nust"`  |
| `class_section`   | string | yes      |                                        |
| `instructor_name` | string | yes      |                                        |
| `course`          | string | yes      |                                        |
| `lab_file`        | file   | yes      | PDF, DOC, or DOCX; max 10MB           |

## Success response — `200`

```json
{
  "status": "success",
  "download_url": "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,<...>"
}
```

As of Phase 7, `download_url` is a real base64 **data URI** containing the
whole generated `.docx`, not a path to a served file — see
`docs/DOCX_GENERATION.md` ("Why `download_url` is a data URI") for the
reasoning and the trade-off it flags. The shape is still `download_url: str`,
so no frontend contract change is needed: use it directly as an
`<a href={downloadUrl} download="lab-report.docx">` target.

> **Naming mismatch, same pattern as the ones below:**
> `frontend/src/types/api.ts` still has this field as `downloadUrl` — no
> code currently reads it (checked as of Phase 7), so this is safe to
> rename to `download_url` whenever Dev A wires up the actual download
> button.

## Error response — `400` or `500`

```json
{
  "status": "error",
  "code": "INVALID_INPUT",
  "message": "Please fix the highlighted fields.",
  "field_errors": {
    "name": ["Value error, Name is required"]
  }
}
```

`field_errors` is only present when `code` is `INVALID_INPUT` — use it to
highlight individual form fields. For every other code, show `message` as a
general error banner.

### Error codes

| Code                     | Meaning                              |
|--------------------------|----------------------------------------|
| `INVALID_INPUT`          | Missing/invalid form fields or no file |
| `UNSUPPORTED_FILE`       | Wrong file type                        |
| `FILE_TOO_LARGE`         | File exceeds 10MB                      |
| `LAB_READ_FAILED`        | Parsing failed (Phase 2+)              |
| `AI_GENERATION_FAILED`   | AI step failed (Phase 3+)              |
| `EXECUTION_FAILED`       | Code execution failed (Phase 4+)       |
| `REPORT_GENERATION_FAILED` | DOCX build failed (Phase 7+)         |

As of Phase 7, every code in this table is reachable — the pipeline is
complete end to end (parsing, AI generation, code execution, screenshots,
and DOCX rendering).

## Interactive docs

FastAPI serves live, always-up-to-date request/response schemas at
`http://localhost:8000/docs` once the backend is running — useful for
double-checking this file hasn't drifted from the actual code.

## Resolved: streaming vs. data URI (was "Open question for 'Together' discussion")

`download_url` stayed a `str` field, now filled with a base64 data URI
rather than a streamed response — see `docs/DOCX_GENERATION.md` for the
reasoning and the size trade-off it flags for the team to revisit later.
