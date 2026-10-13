import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.core.config import settings
from app.core.errors import AppError
from app.schemas.lab import GeneratedLab, ParsedLab

logger = logging.getLogger("labmate.ai")

_DEFAULT_MODEL = "gpt-4o-mini"
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class OpenAIProvider:
    """Concrete AIProvider backed by any OpenAI-compatible chat API.

    The SDK client is built lazily (first real call) so the app starts without
    an API key; a missing key only surfaces when the AI step is reached.

    Hardened for real providers (Groq, Gemini, OpenRouter, local models):
    * request timeout + SDK-level retries for transient errors
    * if the provider rejects `response_format=json_object`, retry without it
    * tolerant JSON extraction (code fences, text around the object)
    * missing optional fields are defaulted instead of failing the report
    * every failure is logged server-side; the user gets an actionable,
      non-leaky message
    """

    def __init__(self, client: AsyncOpenAI | None = None, model: str | None = None) -> None:
        self._client = client
        self._model = model or settings.ai_model or _DEFAULT_MODEL

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.ai_api_key,
                base_url=settings.ai_base_url or None,
                timeout=settings.ai_timeout_seconds,
                max_retries=settings.ai_max_retries,
            )
        return self._client

    async def generate_solutions(self, parsed_lab: ParsedLab) -> GeneratedLab:
        if self._client is None and not settings.ai_api_key:
            logger.error("AI_API_KEY is not set; cannot generate solutions.")
            raise AppError(
                "AI_GENERATION_FAILED",
                "The AI service is not configured on this server (missing API key).",
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(parsed_lab)},
        ]
        try:
            client = self._get_client()
            try:
                response = await client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            except Exception as exc:  # noqa: BLE001
                if not _is_bad_request(exc):
                    raise
                # Some OpenAI-compatible providers/models reject json mode.
                logger.warning("Provider rejected response_format; retrying without it: %s", exc)
                response = await client.chat.completions.create(
                    model=self._model, messages=messages
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("AI request failed")
            raise AppError("AI_GENERATION_FAILED", _friendly_message(exc)) from exc

        raw_content = response.choices[0].message.content or ""
        return _parse_generated_lab(raw_content)


def _status_code(exc: Exception) -> int | None:
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def _is_bad_request(exc: Exception) -> bool:
    return _status_code(exc) == 400


def _friendly_message(exc: Exception) -> str:
    status = _status_code(exc)
    if status in (401, 403):
        return "The AI service rejected the server's API key. Please contact the site owner."
    if status == 404:
        return "The configured AI model was not found. Please contact the site owner."
    if status == 429:
        return "The AI service is busy or out of quota right now. Please try again in a minute."
    if "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower():
        return "The AI service took too long to respond. Please try again."
    return "The AI service could not process this lab right now. Please try again."


def _extract_json(raw: str) -> Any:
    text = _FENCE_RE.sub("", raw.strip()).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def _normalize(data: Any) -> Any:
    """Fill in harmless defaults so one missing optional field doesn't throw
    away an otherwise good generation. Genuinely wrong shapes (no title, no
    tasks list) are left alone and fail validation."""
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        return data
    tasks = []
    for index, task in enumerate(data["tasks"], start=1):
        if not isinstance(task, dict):
            return data
        language = _as_text(task.get("language")).strip().lower()
        code = _as_text(task.get("code"))
        default_ext = {"python": "py", "cpp": "cpp", "c++": "cpp", "c": "c", "java": "java"}.get(
            language, "txt"
        )
        tasks.append(
            {
                "id": _as_text(task.get("id")) or f"task-{index}",
                "description": _as_text(task.get("description")),
                "language": language,
                "filename": _as_text(task.get("filename"))
                or (f"task{index}.{default_ext}" if code.strip() else ""),
                "code": code,
                "explanation": _as_text(task.get("explanation")),
            }
        )
    objectives = data.get("objectives")
    if isinstance(objectives, str):
        objectives = [objectives]
    return {
        "lab_title": data.get("lab_title"),
        "objectives": [_as_text(o) for o in objectives] if isinstance(objectives, list) else [],
        "tasks": tasks,
        "conclusion": _as_text(data.get("conclusion")),
    }


def _parse_generated_lab(raw_content: str) -> GeneratedLab:
    try:
        return GeneratedLab.model_validate(_normalize(_extract_json(raw_content)))
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("AI returned unusable output: %s | first 300 chars: %r", exc, raw_content[:300])
        raise AppError(
            "AI_GENERATION_FAILED",
            "The AI returned an unexpected response. Please try again.",
        ) from exc
