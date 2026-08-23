from pathlib import Path

import yaml

from crypto_lab.api.common import ErrorEnvelope
from crypto_lab.api.schemas.strategy_generation import (
    ActivateGeneratedStrategyRequest,
    CreateStrategyGenerationRequest,
    GeneratedDraftDto,
    GenerationRequestDto,
)
from crypto_lab.main import create_app

CONTRACT = Path(__file__).parents[3] / "specs/003-strategy-foundation/contracts/openapi.yaml"


def test_strategy_openapi_paths_and_boundary_schema_names_stay_in_sync() -> None:
    canonical = yaml.safe_load(CONTRACT.read_text())
    app_paths = create_app().openapi()["paths"]
    for path, methods in canonical["paths"].items():
        full_path = f"/api/v1{path}"
        assert full_path in app_paths
        for method in methods:
            assert method in app_paths[full_path]
    schemas = canonical["components"]["schemas"]
    for required in (
        "StrategyMetadata",
        "Signal",
        "StrategyAnalysisResult",
        "GeneratedStrategyDraft",
        "ValidationReportSummary",
    ):
        assert required in schemas


def test_canonical_error_envelope_matches_the_shared_api_boundary() -> None:
    canonical = yaml.safe_load(CONTRACT.read_text())["components"]["schemas"]
    actual = ErrorEnvelope.model_json_schema(by_alias=True)
    assert set(canonical["ErrorResponse"]["required"]) == set(actual["required"])
    assert set(canonical["ErrorResponse"]["properties"]) == set(actual["properties"])
    assert set(canonical["ErrorDetail"]["required"]) == {"code", "retryable"}
    assert set(canonical["ErrorDetail"]["properties"]) == {
        "code",
        "retryable",
        "details",
    }


def test_generation_boundary_models_are_all_published_by_the_runtime_openapi() -> None:
    runtime_schemas = create_app().openapi()["components"]["schemas"]
    for model in (
        CreateStrategyGenerationRequest,
        GenerationRequestDto,
        GeneratedDraftDto,
        ActivateGeneratedStrategyRequest,
    ):
        assert model.__name__ in runtime_schemas
        schema = model.model_json_schema(by_alias=True)
        assert set(runtime_schemas[model.__name__]["properties"]) == set(schema["properties"])
