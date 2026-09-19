from app.schemas.lab import GeneratedLab, ParsedLab


class FakeAIProvider:
    """Satisfies the AIProvider Protocol without any network dependency —
    used to test AIService/GenerationService orchestration in isolation
    from OpenAIProvider (which is tested separately, with the SDK mocked).
    """

    def __init__(self, result: GeneratedLab | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.received_parsed_lab: ParsedLab | None = None

    async def generate_solutions(self, parsed_lab: ParsedLab) -> GeneratedLab:
        self.received_parsed_lab = parsed_lab
        if self.error:
            raise self.error
        assert self.result is not None
        return self.result
