import pytest

from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion


def test_semantic_version_is_strict_and_ordered() -> None:
    assert SemanticVersion.parse("1.2.3") < SemanticVersion.parse("1.3.0")
    for invalid in ("1", "1.2", "v1.2.3", "1.02.3", "1.2.-1"):
        with pytest.raises(ValueError):
            SemanticVersion.parse(invalid)


def test_contract_range_accepts_same_major_and_inclusive_minor_range() -> None:
    supported = ContractVersionRange(major=1, minimum_minor=0, maximum_minor=2)
    assert supported.supports(SemanticVersion.parse("1.0.99"))
    assert supported.supports(SemanticVersion.parse("1.2.0"))
    assert not supported.supports(SemanticVersion.parse("1.3.0"))
    assert not supported.supports(SemanticVersion.parse("2.0.0"))
