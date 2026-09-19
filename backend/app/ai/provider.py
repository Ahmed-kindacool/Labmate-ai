from typing import Protocol

from app.schemas.lab import GeneratedLab, ParsedLab


class AIProvider(Protocol):
    """Adapter interface per PLAN.md §10: AIService -> AIProvider ->
    OpenAIProvider. Keeps AIService (and everything upstream of it) from
    being tightly coupled to one AI vendor's SDK — swapping providers later
    means writing a new class that satisfies this Protocol, not touching
    the service or the route.
    """

    async def generate_solutions(self, parsed_lab: ParsedLab) -> GeneratedLab: ...
