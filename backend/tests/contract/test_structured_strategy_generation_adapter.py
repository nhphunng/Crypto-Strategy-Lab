from __future__ import annotations

import json

import httpx
import pytest

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.generation import GenerationSourceType
from crypto_lab.infrastructure.llm.strategy_generation_adapter import (
    StructuredStrategyGenerationAdapter,
)

VALID_OUTPUT = {
    "candidates": [
        {
            "normalizedName": "trend-follow",
            "displayName": "Trend Follow",
            "description": "Follows the trend.",
            "structuredRules": {"entry": "close > sma"},
            "parameters": [
                {
                    "name": "period",
                    "description": "Lookback window.",
                    "valueType": "INTEGER",
                    "defaultValue": 20,
                    "minimum": 2,
                    "maximum": 500,
                }
            ],
            "relationships": [],
            "assumptions": ["closed candles only"],
            "evidence": [
                {
                    "ruleId": "entry",
                    "sourceExcerpt": "buy above the moving average",
                    "sourceLocation": "p1",
                    "inferred": False,
                }
            ],
            "sourceCode": "def analyze(candles):\n    return []\n",
        }
    ]
}


def _adapter(
    *,
    transport: httpx.MockTransport,
    max_attempts: int = 3,
    sleep=None,
    provider: str = "test-provider",
) -> tuple[StructuredStrategyGenerationAdapter, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=transport)
    kwargs: dict[str, object] = {"max_attempts": max_attempts}
    if sleep is not None:
        kwargs["sleep"] = sleep
    adapter = StructuredStrategyGenerationAdapter(
        client,
        endpoint="https://provider.example/v1/strategy-generation",
        provider=provider,
        model_id="model-1",
        model_version="1",
        api_key="s3cr3t-key",
        **kwargs,
    )
    return adapter, client


@pytest.mark.asyncio
async def test_successful_generation_returns_candidates_and_never_logs_secret_in_body() -> None:
    seen_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        assert request.headers["Authorization"] == "Bearer s3cr3t-key"
        return httpx.Response(200, json={"output": VALID_OUTPUT})

    adapter, client = _adapter(transport=httpx.MockTransport(handler))
    async with client:
        candidates = await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert len(candidates) == 1
    assert candidates[0].normalized_name == "trend-follow"
    assert candidates[0].source_code.startswith("def analyze")
    assert len(seen_headers) == 1


@pytest.mark.asyncio
async def test_malformed_response_fails_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"output": {"candidates": [{"bogus": True}]}})

    adapter, client = _adapter(transport=httpx.MockTransport(handler), max_attempts=3)
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert "secret" not in str(excinfo.value).lower()
    assert "s3cr3t" not in str(excinfo.value)
    assert calls == 1


@pytest.mark.asyncio
async def test_missing_output_key_fails_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"unexpected": "shape"})

    adapter, client = _adapter(transport=httpx.MockTransport(handler), max_attempts=3)
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert calls == 1


@pytest.mark.asyncio
async def test_rate_limit_honors_retry_after_then_succeeds() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"output": VALID_OUTPUT})

    async def sleep(delay: float) -> None:
        delays.append(delay)

    adapter, client = _adapter(transport=httpx.MockTransport(handler), sleep=sleep)
    async with client:
        candidates = await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert len(candidates) == 1
    assert calls == 2
    assert delays == [2]


@pytest.mark.asyncio
async def test_rate_limit_exhausting_attempts_raises_generation_failed() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "1"})

    async def sleep(delay: float) -> None:
        return None

    adapter, client = _adapter(transport=httpx.MockTransport(handler), max_attempts=2, sleep=sleep)
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert calls == 2


@pytest.mark.asyncio
async def test_provider_5xx_is_retried_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"output": VALID_OUTPUT})

    async def sleep(delay: float) -> None:
        return None

    adapter, client = _adapter(transport=httpx.MockTransport(handler), max_attempts=3, sleep=sleep)
    async with client:
        candidates = await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert len(candidates) == 1
    assert calls == 3


@pytest.mark.asyncio
async def test_client_error_fails_immediately_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"error": "invalid api key"})

    adapter, client = _adapter(transport=httpx.MockTransport(handler), max_attempts=3)
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert calls == 1


@pytest.mark.asyncio
async def test_timeout_is_retried_then_raises_generation_failed() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=request)

    async def sleep(delay: float) -> None:
        return None

    adapter, client = _adapter(transport=httpx.MockTransport(handler), max_attempts=2, sleep=sleep)
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert calls == 2
    assert isinstance(excinfo.value.__cause__, httpx.ReadTimeout)


@pytest.mark.asyncio
async def test_openai_provider_sends_chat_completions_shape_and_parses_message_content() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append(payload)
        assert request.headers["Authorization"] == "Bearer s3cr3t-key"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": json.dumps(VALID_OUTPUT)}}
                ]
            },
        )

    adapter, client = _adapter(transport=httpx.MockTransport(handler), provider="openai")
    async with client:
        candidates = await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert len(candidates) == 1
    assert candidates[0].normalized_name == "trend-follow"
    assert seen[0]["messages"][1]["content"] == "SOURCE_TYPE=STRATEGY_NAME\ntext"
    assert seen[0]["response_format"] == {"type": "json_object"}
    assert "input" not in seen[0]


@pytest.mark.asyncio
async def test_openai_malformed_choices_fails_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"choices": []})

    adapter, client = _adapter(
        transport=httpx.MockTransport(handler), provider="openai", max_attempts=3
    )
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert calls == 1


@pytest.mark.asyncio
async def test_gemini_provider_sends_contents_shape_and_uses_goog_api_key_header() -> None:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        seen.append(payload)
        assert request.headers["x-goog-api-key"] == "s3cr3t-key"
        assert "Authorization" not in request.headers
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_OUTPUT)}]}}]},
        )

    adapter, client = _adapter(transport=httpx.MockTransport(handler), provider="gemini")
    async with client:
        candidates = await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert len(candidates) == 1
    assert seen[0]["contents"][0]["parts"][0]["text"] == "SOURCE_TYPE=STRATEGY_NAME\ntext"
    assert seen[0]["generationConfig"] == {"responseMimeType": "application/json"}
    assert "systemInstruction" in seen[0]


@pytest.mark.asyncio
async def test_gemini_provider_strips_markdown_code_fence_around_json() -> None:
    fenced = "```json\n" + json.dumps(VALID_OUTPUT) + "\n```"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": fenced}]}}]}
        )

    adapter, client = _adapter(transport=httpx.MockTransport(handler), provider="gemini")
    async with client:
        candidates = await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert len(candidates) == 1


@pytest.mark.asyncio
async def test_gemini_provider_empty_candidates_fails_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"candidates": []})

    adapter, client = _adapter(
        transport=httpx.MockTransport(handler), provider="gemini", max_attempts=3
    )
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
    assert calls == 1


@pytest.mark.asyncio
async def test_schema_valid_but_domain_invalid_relationship_operator_fails_cleanly() -> None:
    # A model can satisfy the JSON schema (three strings) while using an operator token
    # RelationshipRule doesn't accept (e.g. "<" instead of "lt"). That must surface as a
    # normal GENERATION_FAILED, not an unhandled crash out of the candidate conversion step.
    bad_candidate = dict(VALID_OUTPUT["candidates"][0])
    bad_candidate["relationships"] = [["period", "<", "threshold"]]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": {"candidates": [bad_candidate]}})

    adapter, client = _adapter(transport=httpx.MockTransport(handler))
    async with client:
        with pytest.raises(StrategyError) as excinfo:
            await adapter.generate(GenerationSourceType.STRATEGY_NAME, "text", "req-1")

    assert excinfo.value.category is ErrorCategory.GENERATION_FAILED
