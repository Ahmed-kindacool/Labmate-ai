import pytest

from app.ai.service import AIService
from app.core.errors import AppError
from app.schemas.lab import GeneratedLab, ParsedLab
from tests.ai_fakes import FakeAIProvider


class TestAIService:
    @pytest.mark.asyncio
    async def test_delegates_to_provider_and_returns_result(
        self, sample_parsed_lab: ParsedLab, sample_generated_lab: GeneratedLab
    ) -> None:
        provider = FakeAIProvider(result=sample_generated_lab)
        service = AIService(provider=provider)

        result = await service.generate_solutions(sample_parsed_lab)

        assert result == sample_generated_lab
        assert provider.received_parsed_lab is sample_parsed_lab

    @pytest.mark.asyncio
    async def test_propagates_provider_errors(self, sample_parsed_lab: ParsedLab) -> None:
        provider = FakeAIProvider(error=AppError("AI_GENERATION_FAILED", "boom"))
        service = AIService(provider=provider)

        with pytest.raises(AppError) as exc_info:
            await service.generate_solutions(sample_parsed_lab)

        assert exc_info.value.code == "AI_GENERATION_FAILED"
