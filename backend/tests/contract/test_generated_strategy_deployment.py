from __future__ import annotations

import base64
from pathlib import Path

import pytest
from pydantic import ValidationError

from crypto_lab.infrastructure.settings import Settings


def test_generation_secrets_load_directly_from_dotenv(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            (
                "CSL_LLM_ENDPOINT=https://provider.example/generate",
                "CSL_LLM_MODEL_ID=fixture-model",
                "CSL_LLM_MODEL_VERSION=1",
                "CSL_LLM_API_KEY=not-a-real-provider-key",
                "CSL_LLM_DATA_POLICY_CONFIRMED=true",
                f"CSL_SOURCE_ENCRYPTION_KEY_BASE64={base64.b64encode(b'k' * 32).decode()}",
            )
        ),
        encoding="utf-8",
    )
    settings = Settings(_env_file=dotenv)

    assert settings.llm_api_key is not None
    assert settings.source_encryption_key_base64 is not None
    assert settings.llm_api_key.get_secret_value() == "not-a-real-provider-key"
    assert base64.b64decode(
        settings.source_encryption_key_base64.get_secret_value(), validate=True
    ) == b"k" * 32


@pytest.mark.parametrize(
    "overrides",
    [
        {"llm_endpoint": "https://provider.example/generate"},
        {
            "llm_endpoint": "https://provider.example/generate",
            "llm_model_id": "model",
            "llm_model_version": "1",
            "llm_api_key": "key",
            "source_encryption_key_base64": base64.b64encode(b"k" * 32).decode(),
        },
    ],
)
def test_partial_or_unacknowledged_generation_configuration_fails_closed(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        Settings(**overrides, _env_file=None)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("llm_api_key", ""),
        ("llm_api_key", "   "),
        ("source_encryption_key_base64", ""),
        ("source_encryption_key_base64", "   "),
    ],
)
def test_empty_generation_secrets_fail_closed(field: str, value: str) -> None:
    configuration: dict[str, object] = {
        "llm_endpoint": "https://provider.example/generate",
        "llm_model_id": "fixture-model",
        "llm_model_version": "1",
        "llm_api_key": "not-a-real-provider-key",
        "llm_data_policy_confirmed": True,
        "source_encryption_key_base64": base64.b64encode(b"k" * 32).decode(),
        field: value,
    }
    with pytest.raises(ValidationError):
        Settings(**configuration, _env_file=None)


def test_encryption_key_without_llm_configuration_supports_restart_only_reuse() -> None:
    settings = Settings(
        source_encryption_key_base64=base64.b64encode(b"k" * 32).decode(),
        _env_file=None,
    )
    assert settings.source_encryption_key_base64 is not None
    assert settings.llm_api_key is None


def test_generated_compose_uses_required_dotenv_secrets_and_dedicated_engine() -> None:
    root = Path(__file__).parents[3]
    compose = (root / "docker-compose.generated.yml").read_text(encoding="utf-8")
    assert "/var/run/docker.sock" not in compose
    assert "CSL_LLM_API_KEY: \"${CSL_LLM_API_KEY:?" in compose
    assert "CSL_SOURCE_ENCRYPTION_KEY_BASE64: \"${CSL_SOURCE_ENCRYPTION_KEY_BASE64:?" in compose
    assert "CSL_LLM_DATA_POLICY_CONFIRMED: \"${CSL_LLM_DATA_POLICY_CONFIRMED:?" in compose
    assert "/run/secrets" not in compose
    assert "_FILE" not in compose
    assert "generated_strategy_artifacts:" in compose
    assert "sandbox-docker:" in compose
    assert "internal: true" in compose
    assert "sandbox-egress:" in compose


def test_dotenv_secrets_and_artifacts_are_excluded_from_git_and_image_context() -> None:
    root = Path(__file__).parents[3]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    dockerignore = (root / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in gitignore
    assert ".env*" in dockerignore
    assert ".data/" in dockerignore


def test_generated_sandbox_receives_no_application_environment() -> None:
    root = Path(__file__).parents[3]
    runtime = (
        root
        / "backend/src/crypto_lab/infrastructure/sandbox/generated_strategy_runtime.py"
    ).read_text(encoding="utf-8")
    assert '"Env": []' in runtime
    assert '"NetworkDisabled": True' in runtime
    assert '"NetworkMode": "none"' in runtime
