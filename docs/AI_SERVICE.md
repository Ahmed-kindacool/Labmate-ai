# AI Service

`backend/app/ai/` implements the `AIService -> AIProvider -> OpenAIProvider`
chain from `PLAN.md` §10. `AIService` and everything above it only depend
on the `AIProvider` Protocol (`app/ai/provider.py`); `OpenAIProvider`
(`app/ai/openai_provider.py`) is the only place that knows about a
specific vendor's SDK.

## Configuration

Set these via `.env` (see `app/core/config.py`):

| Variable       | Required | Notes                                                    |
|----------------|----------|-----------------------------------------------------------|
| `AI_API_KEY`   | yes      | Passed as the SDK client's `api_key`.                      |
| `AI_MODEL`     | no       | Defaults to `gpt-4o-mini` if unset.                        |
| `AI_BASE_URL`  | no       | Defaults to OpenAI's real API if unset — see below.        |

Missing `AI_API_KEY` doesn't crash the app (the client is built lazily —
see the class docstring); it surfaces as `AI_GENERATION_FAILED` only when
a request actually reaches the AI step.

## Using a free-tier provider

The OpenAI Python SDK (`openai`) talks to any endpoint that implements
the same `/chat/completions` shape — it isn't locked to `api.openai.com`.
Several providers offer a free tier that's compatible this way, so
`AI_BASE_URL` was added specifically to let development/testing happen
without an OpenAI billing account:

- **Groq** — the most drop-in option for this codebase. Free tier,
  generous rate limits, and its `llama-3.3-70b-versatile` model supports
  the same `response_format={"type": "json_object"}` JSON mode
  `OpenAIProvider` already asks for, so no code changes beyond config are
  needed.

  ```bash
  AI_API_KEY=<your Groq key>
  AI_BASE_URL=https://api.groq.com/openai/v1
  AI_MODEL=llama-3.3-70b-versatile
  ```

- **Google Gemini** — also has an OpenAI-compatible endpoint on its free
  tier.

  ```bash
  AI_API_KEY=<your Gemini key>
  AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
  AI_MODEL=gemini-2.0-flash
  ```

- **OpenRouter** — aggregates many models, some free (rate-limited,
  usually a `:free` model-name suffix, e.g. `meta-llama/llama-3.3-70b-instruct:free`).
  JSON mode support varies by the underlying model — verify with a real
  request before relying on it.

  ```bash
  AI_API_KEY=<your OpenRouter key>
  AI_BASE_URL=https://openrouter.ai/api/v1
  AI_MODEL=meta-llama/llama-3.3-70b-instruct:free
  ```

**Recommendation for this project specifically:** Groq. The prompts in
`app/ai/prompts.py` ask for strict JSON-only output and real code, and
Groq's free tier is both fast enough for interactive use and reliable
about honoring `response_format`. Gemini's free tier is a reasonable
fallback if Groq's rate limits become a problem. Whichever is used, do
one real (unmocked) smoke test — this sandbox's network egress doesn't
reach any of these APIs, so every provider so far has only been
exercised with the SDK client mocked.

None of this changes `AppError` handling: a bad key, rate limit, or
network error from any of these providers still surfaces as one
`AI_GENERATION_FAILED` message, per `OpenAIProvider.generate_solutions`'s
catch-all.
