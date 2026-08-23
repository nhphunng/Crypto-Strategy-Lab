from crypto_lab.api.schemas.strategy import metadata_to_dto
from crypto_lab.bootstrap.strategies import build_strategy_registry


def test_builtin_discovery_is_deterministic_and_schema_neutral() -> None:
    entries = build_strategy_registry().discover()
    assert [entry.strategy_id for entry in entries] == ["ma", "rsi"]
    payloads = [metadata_to_dto(entry).model_dump(by_alias=True) for entry in entries]
    assert payloads[0]["parameters"][0]["defaultValue"] == 20
    assert payloads[1]["origin"] == "BUILT_IN"
