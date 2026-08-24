from __future__ import annotations

import base64
from pathlib import Path

import pytest
from pydantic import ValidationError

from crypto_lab.infrastructure.settings import Settings


def test_generation_secrets_load_from_files_without_environment_values(tmp_path: Path) -> None:
    llm_key = tmp_path / "llm-key"
    encryption_key = tmp_path / "encryption-key"
    llm_key.write_text("test-provider-key\n", encoding="utf-8")
    encryption_key.write_text(base64.b64encode(b"k" * 32).decode(), encoding="utf-8")

    settings = Settings(
        llm_endpoint="https://provider.example/generate",
        llm_model_id="fixture-model",
        llm_model_version="1",
        llm_api_key_file=str(llm_key),
        llm_data_policy_confirmed=True,
        source_encryption_key_file=str(encryption_key),
        _env_file=None,
    )

    assert settings.resolved_llm_api_key().get_secret_value() == "test-provider-key"
    assert base64.b64decode(
        settings.resolved_source_encryption_key().get_secret_value(), validate=True
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


def test_encryption_key_without_llm_configuration_supports_restart_only_reuse() -> None:
    settings = Settings(
        source_encryption_key_base64=base64.b64encode(b"k" * 32).decode(),
        _env_file=None,
    )
    assert settings.resolved_source_encryption_key() is not None
    assert settings.resolved_llm_api_key() is None


def test_generated_compose_uses_secrets_volume_and_dedicated_engine() -> None:
    root = Path(__file__).parents[3]
    compose = (root / "docker-compose.generated.yml").read_text(encoding="utf-8")
    assert "/var/run/docker.sock" not in compose
    assert "CSL_LLM_API_KEY_FILE: /run/secrets/llm_api_key" in compose
    assert "CSL_SOURCE_ENCRYPTION_KEY_FILE: /run/secrets/source_encryption_key" in compose
    assert "generated_strategy_artifacts:" in compose
    assert "sandbox-docker:" in compose
    assert "internal: true" in compose
    assert "sandbox-egress:" in compose


def test_runtime_secrets_and_artifacts_are_excluded_from_image_build_context() -> None:
    root = Path(__file__).parents[3]
    dockerignore = (root / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".runtime-secrets/" in dockerignore
    assert ".data/" in dockerignore
    assert "*.secret" in dockerignore
