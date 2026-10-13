import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas.generate import AppErrorCode


class AppError(Exception):
    """A user-facing application error. `message` is always safe to display —
    never put stack traces, secrets, or internal paths in it
    (see PROJECT_SPEC.md §7 / docs/SECURITY.md).

    Ported from `AppError` in src/lib/errors/app-error.ts.
    """

    def __init__(
        self,
        code: AppErrorCode,
        message: str,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field_errors = field_errors


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Ported from the `catch` block in src/app/api/generate/route.ts."""
    body = {"status": "error", "code": exc.code, "message": exc.message}
    if exc.field_errors:
        body["field_errors"] = exc.field_errors
    return JSONResponse(status_code=400, content=body)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak stack traces, secrets, or internal paths (PROJECT_SPEC.md §7)."""
    logging.getLogger("labmate").error("Unhandled error on %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "INVALID_INPUT",
            "message": "Something went wrong. Please try again.",
        },
    )
