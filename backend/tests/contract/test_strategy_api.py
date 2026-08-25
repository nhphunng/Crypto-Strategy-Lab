import pytest
from pydantic import ValidationError

from crypto_lab.api.schemas.strategy import StrategyAnalysisRequest


def test_analysis_request_uses_exact_definition_and_forbids_unknown_fields() -> None:
    value = StrategyAnalysisRequest.model_validate(
        {
            "strategyDefinitionId": "00000000-0000-0000-0000-000000000001",
            "datasetId": "dataset",
        }
    )
    assert value.supported_contract_major == 1
    with pytest.raises(ValidationError):
        StrategyAnalysisRequest.model_validate(
            {
                "strategyDefinitionId": "00000000-0000-0000-0000-000000000001",
                "datasetId": "dataset",
                "latest": True,
            }
        )
