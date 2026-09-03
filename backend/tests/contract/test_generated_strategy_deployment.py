from __future__ import annotations

import base64
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
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


def test_generation_secrets_load_from_docker_secret_files(tmp_path: Path) -> None:
    (tmp_path / "CSL_LLM_API_KEY").write_text(
        "not-a-real-provider-key\n", encoding="utf-8"
    )
    (tmp_path / "CSL_SOURCE_ENCRYPTION_KEY_BASE64").write_text(
        base64.b64encode(b"k" * 32).decode(), encoding="utf-8"
    )

    settings = Settings(
        llm_endpoint="https://provider.example/generate",
        llm_model_id="fixture-model",
        llm_model_version="1",
        llm_data_policy_confirmed=True,
        _env_file=None,
        _secrets_dir=tmp_path,
    )

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


def test_production_compose_uses_file_secrets_storage_and_dedicated_engine() -> None:
    root = Path(__file__).parents[3]
    compose_text = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    api = compose["services"]["api"]

    assert "/var/run/docker.sock" not in compose_text
    assert "CSL_LLM_API_KEY" not in api["environment"]
    assert "CSL_SOURCE_ENCRYPTION_KEY_BASE64" not in api["environment"]
    assert {secret["target"] for secret in api["secrets"]} == {
        "CSL_LLM_API_KEY",
        "CSL_SOURCE_ENCRYPTION_KEY_BASE64",
    }
    assert all(set(secret) == {"source", "target"} for secret in api["secrets"])
    assert api["volumes"] == [
        "generated_strategy_artifacts:/var/lib/crypto-lab/generated-strategies"
    ]
    assert api["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert api["depends_on"]["artifact-init"]["condition"] == "service_completed_successfully"
    assert api["depends_on"]["sandbox-docker"]["condition"] == "service_healthy"
    assert "strategy-generation" in " ".join(api["healthcheck"]["test"])
    assert compose["networks"]["sandbox-control"]["internal"] is True
    assert "sandbox-egress" in compose["services"]["sandbox-docker"]["networks"]
    assert set(compose["secrets"]) == {"llm_api_key", "source_encryption_key"}


def test_cd_uses_single_production_compose_and_checks_generation_readiness() -> None:
    root = Path(__file__).parents[3]
    workflow = (root / ".github/workflows/cd.yml").read_text(encoding="utf-8")

    assert "docker-compose.generated.yml" not in workflow
    assert workflow.count("-f docker-compose.prod.yml") >= 4
    assert "/health/ready/strategy-generation" in workflow
    assert "prepare-production-secrets.py" in workflow


def test_cd_secret_preparation_migrates_legacy_values_without_leaking_them(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[3]
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        "\n".join(
            (
                "CSL_LLM_API_KEY=not-a-real-provider-key",
                f"CSL_SOURCE_ENCRYPTION_KEY_BASE64={base64.b64encode(b'k' * 32).decode()}",
            )
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(root / ".github/scripts/prepare-production-secrets.py"),
            "--project-root",
            str(tmp_path),
            "--env-file",
            str(env_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    llm_key = tmp_path / ".runtime-secrets/llm_api_key"
    encryption_key = tmp_path / ".runtime-secrets/source_encryption_key"
    assert llm_key.read_text(encoding="utf-8").strip() == "not-a-real-provider-key"
    assert base64.b64decode(encryption_key.read_text().strip(), validate=True) == b"k" * 32
    assert stat.S_IMODE(llm_key.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(llm_key.stat().st_mode) == 0o444
    assert stat.S_IMODE(encryption_key.stat().st_mode) == 0o444
    assert "not-a-real-provider-key" not in completed.stdout

    env_file.write_text(
        "CSL_LLM_API_KEY=replacement-must-not-overwrite-existing-file\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            str(root / ".github/scripts/prepare-production-secrets.py"),
            "--project-root",
            str(tmp_path),
            "--env-file",
            str(env_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert llm_key.read_text(encoding="utf-8").strip() == "not-a-real-provider-key"


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
