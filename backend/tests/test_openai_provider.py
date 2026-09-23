import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.openai_provider import OpenAIProvider
from app.core.errors import AppError
from app.schemas.lab import GeneratedLab, ParsedLab


def _make_mock_client(content: str) -> MagicMock:
    """Builds a fake AsyncOpenAI client whose
    chat.completions.create(...) returns `content` as the message body,
    matching the real SDK's response shape closely enough for our code to
    read `response.choices[0].message.content`.
    """
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_parses_valid_json_response_into_generated_lab(
        self, sample_parsed_lab: ParsedLab, sample_generated_lab: GeneratedLab
    ) -> None:
        valid_json = sample_generated_lab.model_dump_json()
        client = _make_mock_client(valid_json)
        provider = OpenAIProvider(client=client, model="gpt-4o-mini")

        result = await provider.generate_solutions(sample_parsed_lab)

        assert result == sample_generated_lab
        client.chat.completions.create.assert_awaited_once()
        _, kwargs = client.chat.completions.create.call_args
        assert kwargs["response_format"] == {"type": "json_object"}
        assert kwargs["model"] == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_malformed_json_raises_ai_generation_failed(
        self, sample_parsed_lab: ParsedLab
    ) -> None:
        client = _make_mock_client("not valid json at all")
        provider = OpenAIProvider(client=client, model="gpt-4o-mini")

        with pytest.raises(AppError) as exc_info:
            await provider.generate_solutions(sample_parsed_lab)

        assert exc_info.value.code == "AI_GENERATION_FAILED"

    @pytest.mark.asyncio
    async def test_json_missing_required_fields_raises_ai_generation_failed(
        self, sample_parsed_lab: ParsedLab
    ) -> None:
        # Valid JSON, but doesn't satisfy the GeneratedLab schema.
        client = _make_mock_client(json.dumps({"unexpected": "shape"}))
        provider = OpenAIProvider(client=client, model="gpt-4o-mini")

        with pytest.raises(AppError) as exc_info:
            await provider.generate_solutions(sample_parsed_lab)

        assert exc_info.value.code == "AI_GENERATION_FAILED"

    @pytest.mark.asyncio
    async def test_sdk_exception_raises_ai_generation_failed(
        self, sample_parsed_lab: ParsedLab
    ) -> None:
        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=RuntimeError("network error"))
        provider = OpenAIProvider(client=client, model="gpt-4o-mini")

        with pytest.raises(AppError) as exc_info:
            await provider.generate_solutions(sample_parsed_lab)

        assert exc_info.value.code == "AI_GENERATION_FAILED"
        # The real error is chained, not leaked in the user-facing message.
        assert "network error" not in exc_info.value.message

    def test_construction_never_requires_an_api_key(self) -> None:
        # Regression test: the SDK client used to be built in __init__,
        # which meant the whole app failed to start whenever
        # OPENAI_API_KEY wasn't set. Constructing a provider (or anything
        # that transitively constructs one, like GenerationService) must
        # never touch the SDK until a real call is made.
        OpenAIProvider()  # must not raise, even with no API key configured

    def test_custom_base_url_is_passed_to_the_sdk_client(self, monkeypatch) -> None:
        # Lets a free-tier OpenAI-compatible provider (Groq, Gemini,
        # OpenRouter, ...) be used in place of api.openai.com — see
        # docs/AI_SERVICE.md. Only checks that the setting reaches the
        # SDK client constructor; it doesn't hit a real network endpoint.
        from app.core.config import settings

        monkeypatch.setattr(settings, "ai_api_key", "test-key")
        monkeypatch.setattr(settings, "ai_base_url", "https://api.groq.com/openai/v1")
        provider = OpenAIProvider()
        client = provider._get_client()

        assert str(client.base_url) == "https://api.groq.com/openai/v1/"

    def test_empty_base_url_falls_back_to_sdk_default(self, monkeypatch) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "ai_api_key", "test-key")
        monkeypatch.setattr(settings, "ai_base_url", "")
        provider = OpenAIProvider()
        client = provider._get_client()

        assert "api.openai.com" in str(client.base_url)

    @pytest.mark.asyncio
    async def test_missing_api_key_surfaces_as_ai_generation_failed(
        self, sample_parsed_lab: ParsedLab, monkeypatch
    ) -> None:
        from app.core.config import settings

        monkeypatch.setattr(settings, "ai_api_key", "")
        provider = OpenAIProvider()  # no client injected -> builds a real (keyless) one lazily

        with pytest.raises(AppError) as exc_info:
            await provider.generate_solutions(sample_parsed_lab)

        assert exc_info.value.code == "AI_GENERATION_FAILED"
