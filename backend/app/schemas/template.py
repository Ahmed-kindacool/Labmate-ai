"""Phase 6: shapes for university report templates.

Consumed by `TemplateRegistry` (app/templates_registry) and, in Phase 7,
by the DOCX generator — which needs the on-disk `.docx` template path to
open as its starting document and the logo path to drop into the header.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.domain.university import University


class TemplateConfig(BaseModel):
    """Resolved, on-disk template for one university.

    Both paths are verified to exist by `TemplateRegistry.get_template`
    before this is ever returned — Phase 7 can open them directly without
    re-checking.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    university: University
    template_path: Path
    logo_path: Path
