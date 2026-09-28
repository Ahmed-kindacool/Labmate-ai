from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment variables / `.env`.
    See `.env.example` for every variable with a description of what it
    does and where it's actually used.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_api_key: str = ""
    ai_model: str = ""
    # Optional: point the OpenAI SDK client at an OpenAI-compatible
    # endpoint other than api.openai.com (e.g. a free-tier provider like
    # Groq). Left empty, the SDK's own default (OpenAI's real API) is
    # used. See docs/AI_SERVICE.md "Using a free-tier provider".
    ai_base_url: str = ""
    environment: str = "development"
    max_upload_size_mb: int = 10
    frontend_origin: str = "http://localhost:5173"
    code_execution_enabled: bool = False
    code_execution_timeout_seconds: int = 5


settings = Settings()
