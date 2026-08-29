from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.configuration import (
    CombinationMethod,
    SavedStrategyConfiguration,
    StrategyCombinationRule,
    StrategyConfigurationKind,
    StrategyConfigurationMember,
    StrategyConfigurationSelection,
)
from crypto_lab.domain.strategy.signal import SignalAction
from crypto_lab.infrastructure.persistence.strategy_configuration_models import (
    SavedStrategyConfigurationMemberRow,
    SavedStrategyConfigurationRow,
)


class SqlAlchemyStrategyConfigurationRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(
        self, configuration: SavedStrategyConfiguration
    ) -> SavedStrategyConfiguration:
        async with self._sessions() as session, session.begin():
            existing = await session.scalar(
                select(SavedStrategyConfigurationRow).where(
                    SavedStrategyConfigurationRow.content_fingerprint
                    == configuration.content_fingerprint
                )
            )
            if existing is not None:
                return await self._domain(session, existing)
            latest = await session.scalar(
                select(func.max(SavedStrategyConfigurationRow.configuration_version)).where(
                    SavedStrategyConfigurationRow.configuration_key
                    == configuration.configuration_key
                )
            )
            value = replace(configuration, configuration_version=(latest or 0) + 1)
            await session.execute(
                insert(SavedStrategyConfigurationRow).values(
                    id=value.id,
                    configuration_key=value.configuration_key,
                    configuration_version=value.configuration_version,
                    display_name=value.display_name,
                    kind=value.kind.value,
                    root_definition_id=value.root_definition_id,
                    provider=value.selection.provider,
                    pair=value.selection.pair,
                    timeframe=value.selection.timeframe.value,
                    combination=_combination_values(value.combination),
                    content_fingerprint=value.content_fingerprint,
                    created_at=value.created_at,
                )
            )
            for position, member in enumerate(value.members):
                await session.execute(
                    insert(SavedStrategyConfigurationMemberRow).values(
                        configuration_id=value.id,
                        position=position,
                        strategy_id=member.strategy_id,
                        strategy_version=member.strategy_version,
                        definition_id=member.definition_id,
                        definition_fingerprint=member.definition_fingerprint,
                        parameters=dict(member.parameters),
                        weight=(
                            None if member.weight is None else canonical_decimal(member.weight)
                        ),
                    )
                )
            return value

    async def get(self, configuration_id: UUID) -> SavedStrategyConfiguration | None:
        async with self._sessions() as session:
            row = await session.get(SavedStrategyConfigurationRow, configuration_id)
            return None if row is None else await self._domain(session, row)

    async def get_by_root_definition(
        self, definition_id: UUID
    ) -> SavedStrategyConfiguration | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(SavedStrategyConfigurationRow).where(
                    SavedStrategyConfigurationRow.root_definition_id == definition_id
                )
            )
            return None if row is None else await self._domain(session, row)

    async def list(self) -> tuple[SavedStrategyConfiguration, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(SavedStrategyConfigurationRow).order_by(
                        SavedStrategyConfigurationRow.created_at,
                        SavedStrategyConfigurationRow.id,
                    )
                )
            ).all()
            return tuple([await self._domain(session, row) for row in rows])

    async def _domain(
        self, session: AsyncSession, row: SavedStrategyConfigurationRow
    ) -> SavedStrategyConfiguration:
        member_rows = (
            await session.scalars(
                select(SavedStrategyConfigurationMemberRow)
                .where(SavedStrategyConfigurationMemberRow.configuration_id == row.id)
                .order_by(SavedStrategyConfigurationMemberRow.position)
            )
        ).all()
        return SavedStrategyConfiguration(
            id=row.id,
            configuration_key=row.configuration_key,
            configuration_version=row.configuration_version,
            display_name=row.display_name,
            kind=StrategyConfigurationKind(row.kind),
            root_definition_id=row.root_definition_id,
            selection=StrategyConfigurationSelection(
                row.provider, row.pair, Timeframe(row.timeframe)
            ),
            members=tuple(
                StrategyConfigurationMember(
                    strategy_id=member.strategy_id,
                    strategy_version=member.strategy_version,
                    definition_id=member.definition_id,
                    definition_fingerprint=member.definition_fingerprint,
                    parameters=cast(dict[str, str | int], dict(member.parameters)),
                    weight=None if member.weight is None else Decimal(member.weight),
                )
                for member in member_rows
            ),
            combination=_combination_domain(row.combination),
            created_at=row.created_at,
        )


def _combination_values(rule: StrategyCombinationRule | None) -> dict[str, object] | None:
    if rule is None:
        return None
    return {
        "method": rule.method.value,
        "tieAction": rule.tie_action.value,
        "buyThreshold": canonical_decimal(rule.buy_threshold),
        "sellThreshold": canonical_decimal(rule.sell_threshold),
    }


def _combination_domain(value: dict[str, object] | None) -> StrategyCombinationRule | None:
    if value is None:
        return None
    return StrategyCombinationRule(
        method=CombinationMethod(str(value["method"])),
        tie_action=SignalAction(str(value["tieAction"])),
        buy_threshold=Decimal(str(value["buyThreshold"])),
        sell_threshold=Decimal(str(value["sellThreshold"])),
    )
