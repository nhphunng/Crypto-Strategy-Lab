from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Path, Query, Request, status

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.strategy import (
    CreateStrategyDefinitionRequest,
    StrategyAnalysisDto,
    StrategyAnalysisRequest,
    StrategyDefinitionDto,
    StrategyListDto,
    StrategyMetadataDto,
    analysis_to_dto,
    definition_to_dto,
    metadata_to_dto,
)
from crypto_lab.api.schemas.strategy_configuration import (
    SavedStrategyConfigurationDto,
    SaveStrategyConfigurationRequest,
    StrategyConfigurationListDto,
    configuration_to_dto,
)
from crypto_lab.application.strategies.analyze_strategy import AnalyzeStrategyCommand
from crypto_lab.application.strategies.save_configuration import (
    SaveStrategyConfigurationCommand,
    StrategyCombinationInput,
    StrategyConfigurationMemberInput,
)
from crypto_lab.domain.strategy.configuration import CombinationMethod
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.registry import RegistryStatus
from crypto_lab.domain.strategy.signal import SignalAction
from crypto_lab.domain.strategy.version import ContractVersionRange

router = APIRouter(prefix="/api/v1", tags=["strategies"])


@router.post(
    "/strategy-configurations",
    response_model=SuccessEnvelope[SavedStrategyConfigurationDto],
    status_code=status.HTTP_201_CREATED,
)
async def save_strategy_configuration(
    request: Request, body: SaveStrategyConfigurationRequest
) -> SuccessEnvelope[SavedStrategyConfigurationDto]:
    combination = body.combination
    value = await request.app.state.container.save_strategy_configuration.execute(
        SaveStrategyConfigurationCommand(
            display_name=body.display_name,
            provider=body.selection.provider,
            pair=body.selection.pair,
            timeframe=body.selection.timeframe,
            members=tuple(
                StrategyConfigurationMemberInput(
                    strategy_id=member.strategy_id,
                    strategy_version=member.strategy_version,
                    parameters=member.parameters,
                    weight=None if member.weight is None else Decimal(member.weight),
                )
                for member in body.members
            ),
            combination=None
            if combination is None
            else StrategyCombinationInput(
                method=CombinationMethod(combination.method),
                tie_action=SignalAction(combination.tie_action),
                buy_threshold=Decimal(combination.buy_threshold),
                sell_threshold=Decimal(combination.sell_threshold),
            ),
        )
    )
    dto = (
        SavedStrategyConfigurationDto.model_validate(value)
        if isinstance(value, dict)
        else configuration_to_dto(value)
    )
    return success_envelope(
        dto,
        "Strategy configuration saved.",
        request_id(request),
    )


@router.get(
    "/strategy-configurations",
    response_model=SuccessEnvelope[StrategyConfigurationListDto],
)
async def list_strategy_configurations(
    request: Request,
) -> SuccessEnvelope[StrategyConfigurationListDto]:
    values = await request.app.state.container.strategy_configurations.list()
    return success_envelope(
        StrategyConfigurationListDto(
            configurations=tuple(configuration_to_dto(value) for value in values)
        ),
        "Strategy configurations loaded.",
        request_id(request),
    )


@router.get(
    "/strategy-configurations/{configurationId}",
    response_model=SuccessEnvelope[SavedStrategyConfigurationDto],
)
async def get_strategy_configuration(
    request: Request, configuration_id: UUID = Path(alias="configurationId")
) -> SuccessEnvelope[SavedStrategyConfigurationDto]:
    value = await request.app.state.container.strategy_configurations.get(configuration_id)
    if value is None:
        raise StrategyError(ErrorCategory.UNKNOWN_STRATEGY, "strategy configuration is unavailable")
    return success_envelope(
        configuration_to_dto(value),
        "Strategy configuration loaded.",
        request_id(request),
    )


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


@router.post(
    "/strategy-definitions",
    response_model=SuccessEnvelope[StrategyDefinitionDto],
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy_definition(
    request: Request, body: CreateStrategyDefinitionRequest
) -> SuccessEnvelope[StrategyDefinitionDto]:
    container = request.app.state.container
    entry = container.strategy_discovery.get(body.strategy_id, body.strategy_version)
    metadata = entry.metadata
    if metadata.origin is not StrategyOrigin.BUILT_IN:
        raise StrategyError(
            ErrorCategory.ACTIVATION_NOT_ALLOWED,
            "generated Strategy Definitions must use the reviewed activation workflow",
        )
    parameters = entry.strategy.validate_parameters(body.parameters)
    definition = await container.strategy_definitions.create_or_resolve(
        StrategyDefinition(
            id=uuid4(),
            strategy_id=metadata.strategy_id,
            strategy_type=metadata.strategy_type,
            strategy_version=metadata.strategy_version,
            contract_version=metadata.contract_version,
            parameters=parameters,
            created_at=container.clock.now(),
        )
    )
    return success_envelope(
        definition_to_dto(definition),
        "Strategy Definition created or resolved.",
        request_id(request),
    )


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
