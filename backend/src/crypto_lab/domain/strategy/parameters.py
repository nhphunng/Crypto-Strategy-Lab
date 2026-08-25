from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from types import MappingProxyType

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError

type ParameterScalar = int | Decimal


class ParameterValueType(StrEnum):
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"


def _canonical(value: ParameterScalar) -> str | int:
    return value if isinstance(value, int) else canonical_decimal(value)


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    name: str
    description: str
    value_type: ParameterValueType
    default_value: ParameterScalar | None = None
    minimum: ParameterScalar | None = None
    maximum: ParameterScalar | None = None
    required: bool = False
    minimum_inclusive: bool = True
    maximum_inclusive: bool = True
    allowed_values: frozenset[ParameterScalar] | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.description:
            raise ValueError("parameter name and description are required")


@dataclass(frozen=True, slots=True)
class RelationshipRule:
    left: str
    operator: str
    right: str

    def __post_init__(self) -> None:
        if self.operator not in {"lt", "lte", "gt", "gte"}:
            raise ValueError("unsupported relationship operator")


@dataclass(frozen=True, slots=True)
class ValidatedParameterSet:
    values: Mapping[str, ParameterScalar]
    schema_fingerprint: str
    canonical_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


@dataclass(frozen=True, slots=True)
class ParameterSchema:
    definitions: tuple[ParameterDefinition, ...]
    relationship_rules: tuple[RelationshipRule, ...] = ()

    def __post_init__(self) -> None:
        names = [definition.name for definition in self.definitions]
        if len(names) != len(set(names)):
            raise ValueError("parameter names must be unique")
        known = set(names)
        if any(
            rule.left not in known or rule.right not in known for rule in self.relationship_rules
        ):
            raise ValueError("relationship references an unknown parameter")
        for definition in self.definitions:
            if definition.default_value is not None:
                self._coerce_and_check(definition, definition.default_value)

    @property
    def fingerprint(self) -> str:
        payload = [
            {
                "name": item.name,
                "type": item.value_type.value,
                "default": None if item.default_value is None else _canonical(item.default_value),
                "minimum": None if item.minimum is None else _canonical(item.minimum),
                "maximum": None if item.maximum is None else _canonical(item.maximum),
                "required": item.required,
            }
            for item in self.definitions
        ]
        relationships = [(rule.left, rule.operator, rule.right) for rule in self.relationship_rules]
        return hashlib.sha256(
            json.dumps([payload, relationships], separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()

    def validate(self, raw: Mapping[str, object]) -> ValidatedParameterSet:
        definitions = {item.name: item for item in self.definitions}
        issues: list[ErrorIssue] = []
        values: dict[str, ParameterScalar] = {}
        for unknown in sorted(set(raw) - set(definitions)):
            issues.append(ErrorIssue(unknown, "UNKNOWN", "parameter is not defined"))
        for definition in self.definitions:
            if definition.name in raw:
                supplied = raw[definition.name]
            elif definition.default_value is not None:
                supplied = definition.default_value
            elif definition.required:
                issues.append(ErrorIssue(definition.name, "REQUIRED", "parameter is required"))
                continue
            else:
                continue
            try:
                values[definition.name] = self._coerce_and_check(definition, supplied)
            except (TypeError, ValueError, InvalidOperation) as exc:
                issues.append(ErrorIssue(definition.name, "INVALID", str(exc)))
        for rule in self.relationship_rules:
            if rule.left not in values or rule.right not in values:
                continue
            left, right = values[rule.left], values[rule.right]
            valid = {
                "lt": left < right,
                "lte": left <= right,
                "gt": left > right,
                "gte": left >= right,
            }[rule.operator]
            if not valid:
                issues.append(
                    ErrorIssue(rule.left, "RELATIONSHIP", f"must be {rule.operator} {rule.right}")
                )
        if issues:
            raise StrategyError(
                ErrorCategory.INVALID_PARAMETERS, "strategy parameters are invalid", tuple(issues)
            )
        ordered = {name: values[name] for name in sorted(values)}
        canonical = {name: _canonical(value) for name, value in ordered.items()}
        digest = hashlib.sha256(
            json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        return ValidatedParameterSet(ordered, self.fingerprint, digest)

    @staticmethod
    def _coerce_and_check(definition: ParameterDefinition, value: object) -> ParameterScalar:
        if isinstance(value, bool | float):
            raise TypeError("bool and float are not accepted")
        if definition.value_type is ParameterValueType.INTEGER:
            if not isinstance(value, int):
                raise TypeError("must be an integer")
            result: ParameterScalar = value
        else:
            if not isinstance(value, str | int | Decimal):
                raise TypeError("must be an exact decimal string, integer, or Decimal")
            result = value if isinstance(value, Decimal) else Decimal(value)
            if not result.is_finite():
                raise ValueError("must be finite")
        if definition.minimum is not None and (
            result < definition.minimum
            or (result == definition.minimum and not definition.minimum_inclusive)
        ):
            raise ValueError("below minimum")
        if definition.maximum is not None and (
            result > definition.maximum
            or (result == definition.maximum and not definition.maximum_inclusive)
        ):
            raise ValueError("above maximum")
        if definition.allowed_values is not None and result not in definition.allowed_values:
            raise ValueError("value is not allowed")
        return result
