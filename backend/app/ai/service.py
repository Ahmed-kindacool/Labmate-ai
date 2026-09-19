from app.ai.openai_provider import OpenAIProvider
from app.ai.provider import AIProvider
from app.schemas.lab import GeneratedLab, ParsedLab


class AIService:
    """Thin coordination layer over an AIProvider. Exists as its own class
    (rather than calling OpenAIProvider directly from GenerationService) so
    provider-swapping and future cross-cutting concerns (retries, caching,
    logging) have one home, per PLAN.md §10's AIService -> AIProvider split.
    """

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider or OpenAIProvider()

    async def generate_solutions(self, parsed_lab: ParsedLab) -> GeneratedLab:
        return await self._provider.generate_solutions(parsed_lab)
