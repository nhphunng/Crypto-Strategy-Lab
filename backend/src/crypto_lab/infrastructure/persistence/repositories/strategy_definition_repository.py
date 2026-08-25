from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.parameters import ValidatedParameterSet
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow


class SqlAlchemyStrategyDefinitionRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create_or_resolve(self, definition: StrategyDefinition) -> StrategyDefinition:
        values = {
            key: value if isinstance(value, int) else canonical_decimal(value)
            for key, value in definition.parameters.values.items()
        }
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(StrategyDefinitionRow)
                .values(
                    id=definition.id,
                    strategy_id=definition.strategy_id,
                    strategy_type=definition.strategy_type,
                    strategy_version=str(definition.strategy_version),
                    contract_version=str(definition.contract_version),
                    parameters=values,
                    parameter_schema_fingerprint=definition.parameters.schema_fingerprint,
                    content_fingerprint=definition.content_fingerprint,
                    created_at=definition.created_at,
                    origin=definition.origin.value,
                    generated_artifact_id=definition.generated_artifact_id,
                    generation_provenance_id=definition.generation_provenance_id,
                )
                .on_conflict_do_nothing(index_elements=["content_fingerprint"])
            )
            row = await session.scalar(
                select(StrategyDefinitionRow).where(
                    StrategyDefinitionRow.content_fingerprint == definition.content_fingerprint
                )
            )
            if row is None:
                raise RuntimeError("strategy definition insert could not be resolved")
            return _to_domain(row)

    async def get(self, definition_id: UUID) -> StrategyDefinition | None:
        async with self._sessions() as session:
            row = await session.get(StrategyDefinitionRow, definition_id)
        return None if row is None else _to_domain(row)

    async def find_exact(
        self, strategy_id: str, strategy_version: SemanticVersion
    ) -> tuple[StrategyDefinition, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(StrategyDefinitionRow)
                    .where(
                        StrategyDefinitionRow.strategy_id == strategy_id,
                        StrategyDefinitionRow.strategy_version == str(strategy_version),
                    )
                    .order_by(StrategyDefinitionRow.created_at, StrategyDefinitionRow.id)
                )
            ).all()
        return tuple(_to_domain(row) for row in rows)


def _to_domain(row: StrategyDefinitionRow) -> StrategyDefinition:
    values = {
        key: value if isinstance(value, int) else Decimal(str(value))
        for key, value in row.parameters.items()
    }
    canonical = {
        key: value if isinstance(value, int) else canonical_decimal(value)
        for key, value in values.items()
    }
    parameter_fingerprint = hashlib.sha256(
        json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    parameters = ValidatedParameterSet(
        values,
        row.parameter_schema_fingerprint,
        parameter_fingerprint,
    )
    return StrategyDefinition(
        id=row.id,
        strategy_id=row.strategy_id,
        strategy_type=row.strategy_type,
        strategy_version=SemanticVersion.parse(row.strategy_version),
        contract_version=SemanticVersion.parse(row.contract_version),
        parameters=parameters,
        created_at=row.created_at,
        origin=StrategyOrigin(row.origin),
        generated_artifact_id=row.generated_artifact_id,
        generation_provenance_id=row.generation_provenance_id,
    )
