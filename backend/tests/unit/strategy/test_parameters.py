from decimal import Decimal

import pytest

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.parameters import (
    ParameterDefinition,
    ParameterSchema,
    ParameterValueType,
    RelationshipRule,
)


def test_defaults_and_equivalent_decimals_have_canonical_fingerprint() -> None:
    schema = ParameterSchema(
        (
            ParameterDefinition("period", "Window", ParameterValueType.INTEGER, 20, 2, 500),
            ParameterDefinition(
                "threshold",
                "Level",
                ParameterValueType.DECIMAL,
                Decimal("30"),
                Decimal("0"),
                Decimal("100"),
            ),
        )
    )
    first = schema.validate({})
    second = schema.validate({"period": 20, "threshold": "30.0"})
    assert first.values == second.values
    assert first.canonical_fingerprint == second.canonical_fingerprint


def test_validation_reports_all_unknown_type_range_and_relationship_issues() -> None:
    schema = ParameterSchema(
        (
            ParameterDefinition(
                "lower",
                "Lower",
                ParameterValueType.DECIMAL,
                Decimal("30"),
                Decimal("0"),
                Decimal("100"),
            ),
            ParameterDefinition(
                "upper",
                "Upper",
                ParameterValueType.DECIMAL,
                Decimal("70"),
                Decimal("0"),
                Decimal("100"),
            ),
        ),
        (RelationshipRule("lower", "lt", "upper"),),
    )
    with pytest.raises(StrategyError) as caught:
        schema.validate({"lower": "101", "upper": "bad", "extra": 1})
    assert caught.value.category is ErrorCategory.INVALID_PARAMETERS
    assert {issue.field for issue in caught.value.issues} == {"lower", "upper", "extra"}
