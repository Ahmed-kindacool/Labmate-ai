import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.routes import health, lab

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("labmate")

app = FastAPI(title="LabMate AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(health.router, prefix="/api/v1")
app.include_router(lab.router, prefix="/api/v1")


@app.on_event("startup")
async def _log_configuration() -> None:
    logger.info(
        "AI configured: %s | code execution: %s (%s)",
        "yes" if settings.ai_api_key else "NO (set AI_API_KEY)",
        "enabled" if settings.code_execution_enabled else "disabled",
        settings.code_execution_mode,
    )


# Production: serve the built SPA from the same origin as the API, so there is
# no CORS or API-URL configuration at all. Registered last so /api/* wins.
_dist = Path(settings.frontend_dist_dir) if settings.frontend_dist_dir else None
if _dist is not None and (_dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
    logger.info("Serving frontend from %s", _dist)
