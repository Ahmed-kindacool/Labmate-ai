import json

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.config import settings
from app.core.errors import AppError
from app.schemas.lab import GeneratedLab, ParsedLab

_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider:
    """Concrete AIProvider backed by the OpenAI API.

    Per PLAN.md §10, this is intentionally the only place in the codebase
    that knows about OpenAI specifically — AIService and everything above
    it only depend on the AIProvider Protocol.

    The SDK client is built lazily (on first real call), not in
    __init__. The app wires up a GenerationService -> AIService ->
    OpenAIProvider chain at import time (see routes/lab.py's module-level
    singleton); if the client were constructed eagerly, the entire app
    would fail to start whenever OPENAI_API_KEY isn't set yet — e.g. local
    dev before a key exists, or a Phase 1/2-only deployment. A missing key
    should only ever surface as an AI_GENERATION_FAILED response, when the
    AI step is actually reached.
    """

    def __init__(self, client: AsyncOpenAI | None = None, model: str | None = None) -> None:
        self._client = client
        self._model = model or settings.ai_model or _DEFAULT_MODEL

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.ai_api_key)
        return self._client

    async def generate_solutions(self, parsed_lab: ParsedLab) -> GeneratedLab:
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(parsed_lab)},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            # Covers a missing/invalid API key, rate limits, timeouts, and
            # network errors — all surfaced to the student as one friendly,
            # non-leaky message.
            raise AppError(
                "AI_GENERATION_FAILED",
                "The AI service could not process this lab right now. Please try again.",
            ) from exc

        raw_content = response.choices[0].message.content or ""
        return _parse_generated_lab(raw_content)


def _parse_generated_lab(raw_content: str) -> GeneratedLab:
    try:
        data = json.loads(raw_content)
        return GeneratedLab.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AppError(
            "AI_GENERATION_FAILED",
            "The AI returned an unexpected response. Please try again.",
        ) from exc
