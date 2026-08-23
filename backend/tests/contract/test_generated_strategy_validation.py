from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import _static_checks


def test_generated_artifact_static_contract_accepts_bounded_entrypoint() -> None:
    checks, findings = _static_checks(
        "from decimal import Decimal\ndef analyze(payload):\n return {'signals': []}\n"
    )
    assert all(item.passed for item in checks)
    assert findings == ()


def test_generated_artifact_rejects_io_dynamic_code_and_network_imports() -> None:
    checks, _ = _static_checks(
        "import socket\ndef analyze(payload):\n return eval(payload['code'])\n"
    )
    failed = {item.name for item in checks if not item.passed}
    assert failed == {"import_allowlist", "forbidden_builtins"}


def test_generated_artifact_import_metadata_must_match_actual_ast_imports() -> None:
    checks, findings = _static_checks(
        "import math\ndef analyze(payload):\n return {'signals': []}\n",
        frozenset(),
    )
    assert {item.name for item in checks if not item.passed} == {"declared_imports"}
    assert findings[0].code == "IMPORT_METADATA_MISMATCH"
