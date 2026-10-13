from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env next to the backend, not relative to the current directory --
# otherwise starting uvicorn from the repo root (or an IDE run config) silently
# loads NO settings and the AI key looks "missing".
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Ported from `EnvSchema` in src/lib/env.ts.

    Note: the original `getEnv()` was never actually imported/called anywhere
    in the source repo — it was Phase-ahead scaffolding. Same status here:
    defined for when Phase 3+ (AI provider, code execution) needs it, not
    wired into the request path yet.
    """

    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), ".env"), extra="ignore"
    )

    ai_api_key: str = ""
    ai_model: str = ""
    # Optional: point the OpenAI SDK client at an OpenAI-compatible
    # endpoint other than api.openai.com (e.g. a free-tier provider like
    # Groq). Left empty, the SDK's own default (OpenAI's real API) is
    # used. See docs/AI_SERVICE.md "Using a free-tier provider".
    ai_base_url: str = ""
    environment: str = "development"
    max_upload_size_mb: int = 10
    # Comma-separated list of allowed browser origins.
    frontend_origin: str = "http://localhost:5173"
    code_execution_enabled: bool = False
    # "docker": one throwaway container per run (needs the docker CLI + daemon).
    # "local":  run as a locked-down child process of this server (rlimits,
    #           stripped env, own process group, privileges dropped to
    #           `nobody` when started as root). Meant for deployments where
    #           the app itself already runs in a disposable container
    #           (Render, Railway, Fly, a plain Dockerfile) and Docker-in-Docker
    #           is not available. See docs/DEPLOYMENT.md.
    code_execution_mode: str = "docker"
    code_execution_timeout_seconds: float = 10
    # Compiling C/C++ is not "the program running too long"; give it its own budget.
    code_compile_timeout_seconds: float = 30
    ai_timeout_seconds: float = 120
    ai_max_retries: int = 2
    # Directory holding the built frontend (frontend/dist). When set and it
    # exists, the backend serves the SPA itself, so UI + API share one origin.
    frontend_dist_dir: str = ""


    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()
