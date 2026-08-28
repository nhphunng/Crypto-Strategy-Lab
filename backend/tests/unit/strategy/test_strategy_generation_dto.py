from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from crypto_lab.api.schemas.strategy_generation import request_dto
from crypto_lab.domain.strategy.generation import (
    GenerationRequestStatus,
    GenerationSourceType,
    StrategyGenerationRequest,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _request(**overrides: object) -> StrategyGenerationRequest:
    defaults: dict[str, object] = dict(
        id=UUID(int=1),
        source_type=GenerationSourceType.STRATEGY_NAME,
        submitted_value="donchian breakout",
        status=GenerationRequestStatus.RECEIVED,
        requested_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return StrategyGenerationRequest(**defaults)  # type: ignore[arg-type]


def test_completed_request_has_no_failure() -> None:
    dto = request_dto(_request(status=GenerationRequestStatus.COMPLETED), ())
    assert dto.failure is None


def test_failed_request_surfaces_category_and_message() -> None:
    request = _request(
        status=GenerationRequestStatus.FAILED,
        failure_category="STRATEGY_INTENT_UNRESOLVED",
        failure_message="strategy name could not be resolved to exactly one trading concept",
    )
    dto = request_dto(request, ())
    assert dto.failure == {
        "code": "STRATEGY_INTENT_UNRESOLVED",
        "message": "strategy name could not be resolved to exactly one trading concept",
    }
