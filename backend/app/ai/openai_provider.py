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
            response = await self._complete(messages)
        except Exception as exc:  # noqa: BLE001
            logger.exception("AI request failed")
            raise AppError("AI_GENERATION_FAILED", _friendly_message(exc)) from exc

        choice = response.choices[0]
        raw_content = choice.message.content or ""
        finish_reason = _text_or_none(getattr(choice, "finish_reason", None))
        logger.info("AI finished: %s", _usage_summary(response, finish_reason))

        if not raw_content.strip():
            logger.error(
                "AI returned empty content (%s). For reasoning models the thinking "
                "tokens share the output budget: raise AI_MAX_OUTPUT_TOKENS or lower "
                "AI_REASONING_EFFORT.",
                _usage_summary(response, finish_reason),
            )
            raise AppError("AI_GENERATION_FAILED", _empty_message(finish_reason))
        return _parse_generated_lab(raw_content, truncated=finish_reason == "length")

    def _reasoning_effort(self) -> str | None:
        configured = settings.ai_reasoning_effort.strip().lower()
        if configured:
            return configured
        # Reasoning models burn the output budget on hidden thinking; this is
        # structured extraction, so keep it short. Only auto-applied where the
        # parameter is known to be accepted (other providers may reject it).
        return "low" if "gpt-oss" in self._model.lower() else None

    async def _complete(self, messages: list[dict[str, str]]):
        """Sends the request, degrading gracefully if the provider rejects a
        parameter (400): full -> without JSON mode -> bare minimum."""
        client = self._get_client()
        effort = self._reasoning_effort()
        base: dict[str, Any] = {"model": self._model, "messages": messages}
        tuned = dict(base, max_completion_tokens=settings.ai_max_output_tokens)
        if effort:
            tuned["extra_body"] = {"reasoning_effort": effort}

        variants = [
            ("full", dict(tuned, response_format={"type": "json_object"})),
            ("without JSON mode", tuned),
            ("minimal", dict(base, max_tokens=settings.ai_max_output_tokens)),
        ]
        last_error: Exception | None = None
        for label, params in variants:
            try:
                return await client.chat.completions.create(**params)
            except Exception as exc:  # noqa: BLE001
                if not _is_bad_request(exc):
                    raise
                last_error = exc
                logger.warning("Provider rejected the request (%s variant); trying a simpler one: %s", label, exc)
        assert last_error is not None
        raise last_error


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
    if status == 413:
        return (
            "This lab is too large for the AI model's per-minute token limit. "
            "Try a shorter lab, or ask the site owner to use a model with a higher limit."
        )
    if status == 429:
        return "The AI service is busy or out of quota right now. Please try again in a minute."
    if "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower():
        return "The AI service took too long to respond. Please try again."
    return "The AI service could not process this lab right now. Please try again."


def _text_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _usage_summary(response: Any, finish_reason: str | None) -> str:
    usage = getattr(response, "usage", None)
    completion = getattr(usage, "completion_tokens", None)
    details = getattr(usage, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None)
    parts = [f"finish_reason={finish_reason}"]
    if isinstance(completion, int):
        parts.append(f"completion_tokens={completion}")
    if isinstance(reasoning, int):
        parts.append(f"reasoning_tokens={reasoning}")
    parts.append(f"budget={settings.ai_max_output_tokens}")
    return " ".join(parts)


def _empty_message(finish_reason: str | None) -> str:
    if finish_reason == "length":
        return (
            "The AI ran out of output space before finishing this lab. Please try a "
            "smaller lab, or ask the site owner to raise the AI output limit."
        )
    return "The AI returned an empty response. Please try again."


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
        default_ext = {
            "python": "py", "cpp": "cpp", "c++": "cpp", "c": "c", "java": "java",
            "kotlin": "kt", "xml": "xml", "html": "html", "css": "css",
            "javascript": "js", "sql": "sql",
        }.get(language, "txt")
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
        "steps": _normalize_steps(data.get("steps")),
        "tables": _normalize_tables(data.get("tables")),
        "screenshots": _normalize_screenshots(data.get("screenshots")),
        "code_as_text": data.get("code_as_text") is True
        or _as_text(data.get("code_as_text")).strip().lower() == "true",
    }


def _normalize_steps(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    steps = []
    for item in raw:
        if isinstance(item, dict):
            steps.append(
                {
                    "title": _as_text(item.get("title")),
                    "details": _as_text(item.get("details") or item.get("what")),
                    "location": _as_text(item.get("location") or item.get("where")),
                    "issue": _as_text(item.get("issue") or item.get("problem")),
                }
            )
        elif isinstance(item, str) and item.strip():
            steps.append({"title": "", "details": item, "location": "", "issue": ""})
    return steps


def _normalize_tables(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    tables = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("rows"), list):
            continue
        headers = [_as_text(h) for h in item.get("headers") or []]
        rows = [
            [_as_text(cell) for cell in row] if isinstance(row, list) else [_as_text(row)]
            for row in item["rows"]
        ]
        tables.append({"title": _as_text(item.get("title")), "headers": headers, "rows": rows})
    return tables


def _normalize_screenshots(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    captions = []
    for item in raw:
        text = _as_text(item.get("caption")) if isinstance(item, dict) else _as_text(item)
        if text.strip():
            captions.append(text.strip())
    return captions


def _parse_generated_lab(raw_content: str, truncated: bool = False) -> GeneratedLab:
    try:
        return GeneratedLab.model_validate(_normalize(_extract_json(raw_content)))
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error(
            "AI returned unusable output (truncated=%s): %s | first 300 chars: %r",
            truncated, exc, raw_content[:300],
        )
        raise AppError(
            "AI_GENERATION_FAILED",
            _empty_message("length")
            if truncated
            else "The AI returned an unexpected response. Please try again.",
        ) from exc
