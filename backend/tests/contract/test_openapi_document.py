from pathlib import Path

import yaml

from crypto_lab.main import create_app
from tests.contract.test_market_data_api import build_test_container

CONTRACT = (
    Path(__file__).parents[3]
    / "specs"
    / "001-historical-market-data"
    / "contracts"
    / "openapi.yaml"
)


def test_openapi_contract_is_valid_yaml_and_runtime_paths_are_present() -> None:
    documented = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    container, _ = build_test_container()
    runtime = create_app(container).openapi()

    required_paths = {
        "/market-data/dimensions",
        "/market-data/candles",
        "/market-data/datasets",
        "/market-data/datasets/{datasetId}",
        "/market-data/datasets/{datasetId}/candles",
    }
    assert documented["openapi"] == "3.1.0"
    assert required_paths == set(documented["paths"])
    assert {f"/api/v1{path}" for path in required_paths} <= set(runtime["paths"])
    assert documented["components"]["schemas"]["Timeframe"]["enum"] == [
        "1m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "1d",
    ]
