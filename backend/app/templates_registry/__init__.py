"""Phase 6: university report templates.

Ported from the Phase 2 stub (`backend/app/templates_registry/__init__.py`
on `origin/main`), which only stored three hardcoded, CWD-relative path
strings and raised a plain `ValueError`. Rebuilt here per
`docs/TEMPLATES_AND_UI.md`:

- Paths are resolved relative to this file, not the process's current
  working directory -- the Phase 2 stub's `"backend/templates_registry/..."`
  strings only resolved correctly if the server happened to be launched
  from the repo root.
- Failures raise `AppError` (the project's convention -- see
  `app/core/errors.py`) instead of a bare `ValueError`, so they turn into
  a proper `GenerateErrorResponse` instead of an unhandled 500.
- `get_template` verifies the `.docx` and logo actually exist on disk
  before returning, since a wrong or missing file here would otherwise
  only surface later, inside Phase 7's DOCX generation.
- Returns a `TemplateConfig`, not a loose `Dict[str, Any]`, so Phase 7
  gets real attribute access and type checking.

The on-disk layout matches `TEMPLATES_AND_UI.md` exactly:

    backend/templates_registry/templates/
    |-- air/{template.docx, logo.png}
    |-- bahria/{template.docx, logo.png}
    `-- nust/{template.docx, logo.png}

All three `template.docx` files share the same layout/formatting; only
the embedded logo differs per university. The university name is never
inserted into the document as text (PROJECT_SPEC.md / TEMPLATES_AND_UI.md
"Critical requirement") -- selecting a university only ever selects which
template/logo pair is used.
"""

from pathlib import Path

from app.core.errors import AppError
from app.domain.university import University
from app.schemas.template import TemplateConfig

# backend/app/templates_registry/__init__.py -> backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATES_ROOT = _BACKEND_ROOT / "templates_registry" / "templates"

_TEMPLATE_FILENAME = "template.docx"
_LOGO_FILENAME = "logo.png"


class TemplateRegistry:
    """Resolves a `University` to its on-disk template + logo."""

    def __init__(self, templates_root: Path = _TEMPLATES_ROOT) -> None:
        self._templates_root = templates_root

    def get_template(self, university: University | str) -> TemplateConfig:
        """Returns the verified, on-disk template config for `university`.

        Raises `AppError` (code `REPORT_GENERATION_FAILED`) if the
        university is unrecognized, or if its template/logo files are
        missing from disk -- both are report-generation-blocking
        conditions, and there's no more specific `AppErrorCode` for a
        template-lookup failure (see `app/schemas/generate.py`).
        """
        try:
            uni = university if isinstance(university, University) else University(university.lower())
        except ValueError as exc:
            raise AppError(
                "REPORT_GENERATION_FAILED",
                f"No report template is configured for '{university}'.",
            ) from exc

        uni_dir = self._templates_root / uni.value
        template_path = uni_dir / _TEMPLATE_FILENAME
        logo_path = uni_dir / _LOGO_FILENAME

        missing = [p for p in (template_path, logo_path) if not p.is_file()]
        if missing:
            missing_names = ", ".join(p.name for p in missing)
            raise AppError(
                "REPORT_GENERATION_FAILED",
                f"The report template for '{uni.value}' is missing required "
                f"file(s): {missing_names}.",
            )

        return TemplateConfig(
            university=uni,
            template_path=template_path,
            logo_path=logo_path,
        )
