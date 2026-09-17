from collections import defaultdict

from fastapi import APIRouter, Form, UploadFile
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.generate import GenerateSuccessResponse
from app.schemas.student import StudentInfo
from app.services.generation_service import GenerationService
from app.validation.lab_file import validate_lab_file

router = APIRouter()
generation_service = GenerationService()


@router.post("/labs/generate", response_model=GenerateSuccessResponse)
async def generate_lab_report(
    name: str | None = Form(None),
    roll_number: str | None = Form(None),
    university: str | None = Form(None),
    class_section: str | None = Form(None),
    instructor_name: str | None = Form(None),
    course: str | None = Form(None),
    lab_file: UploadFile | None = None,
) -> GenerateSuccessResponse:
    """Ported from the POST handler in src/app/api/generate/route.ts.

    Field names follow the migration spec's snake_case contract
    (name, roll_number, class_section, instructor_name, course, lab_file)
    instead of the original camelCase JS field names.
    """
    raw_fields = {
        "name": name,
        "roll_number": roll_number,
        "university": university,
        "class_section": class_section,
        "instructor_name": instructor_name,
        "course": course,
    }

    try:
        student = StudentInfo.model_validate(raw_fields)
    except ValidationError as exc:
        field_errors: dict[str, list[str]] = defaultdict(list)
        for error in exc.errors():
            field = str(error["loc"][0]) if error["loc"] else "unknown"
            field_errors[field].append(error["msg"])
        raise AppError(
            "INVALID_INPUT",
            "Please fix the highlighted fields.",
            dict(field_errors),
        )

    if lab_file is None:
        raise AppError("INVALID_INPUT", "A lab file (PDF, DOC, or DOCX) is required.")

    # Read once to get the real size; UploadFile.size is not always populated
    # depending on the ASGI server, so this mirrors the JS File object's
    # `.size` more faithfully than trusting the header.
    lab_bytes = await lab_file.read()
    file_error = validate_lab_file(lab_file.content_type, len(lab_bytes))
    if file_error:
        code = "FILE_TOO_LARGE" if "large" in file_error else "UNSUPPORTED_FILE"
        raise AppError(code, file_error)

    return await generation_service.generate(
        student=student,
        lab_filename=lab_file.filename or "",
        lab_content_type=lab_file.content_type or "",
        lab_bytes=lab_bytes,
    )
