from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.strategy import (
    StrategyAnalysisDto,
    StrategyAnalysisRequest,
    StrategyListDto,
    StrategyMetadataDto,
    analysis_to_dto,
    metadata_to_dto,
)
from crypto_lab.application.strategies.analyze_strategy import AnalyzeStrategyCommand
from crypto_lab.domain.strategy.registry import RegistryStatus
from crypto_lab.domain.strategy.version import ContractVersionRange

router = APIRouter(prefix="/api/v1", tags=["strategies"])


@router.get("/strategies", response_model=SuccessEnvelope[StrategyListDto])
async def discover_strategies(
    request: Request,
    status: RegistryStatus | None = Query(default=RegistryStatus.AVAILABLE),
) -> SuccessEnvelope[StrategyListDto]:
    entries = request.app.state.container.strategy_discovery.list(status)
    return success_envelope(
        StrategyListDto(strategies=tuple(metadata_to_dto(item) for item in entries)),
        "Strategies loaded.",
        request_id(request),
    )


@router.get(
    "/strategies/{strategyId}/versions/{strategyVersion}",
    response_model=SuccessEnvelope[StrategyMetadataDto],
)
async def get_strategy_version(
    request: Request,
    strategy_id: str = Path(alias="strategyId"),
    strategy_version: str = Path(alias="strategyVersion"),
) -> SuccessEnvelope[StrategyMetadataDto]:
    entry = request.app.state.container.strategy_discovery.get(strategy_id, strategy_version)
    return success_envelope(metadata_to_dto(entry), "Strategy loaded.", request_id(request))


@router.post("/strategy-analyses", response_model=SuccessEnvelope[StrategyAnalysisDto])
async def analyze_strategy(
    request: Request, body: StrategyAnalysisRequest
) -> SuccessEnvelope[StrategyAnalysisDto]:
    result = await request.app.state.container.strategy_analysis.execute(
        AnalyzeStrategyCommand(
            request_id=request_id(request),
            definition_id=body.strategy_definition_id,
            dataset_id=body.dataset_id,
            supported_contract=ContractVersionRange(
                body.supported_contract_major,
                body.minimum_contract_minor,
                body.maximum_contract_minor,
            ),
        )
    )
    return success_envelope(analysis_to_dto(result), "Strategy analyzed.", request_id(request))
