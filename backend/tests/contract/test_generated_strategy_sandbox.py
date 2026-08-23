import shutil
import subprocess
from pathlib import Path

import pytest

from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)

ROOT = Path(__file__).parents[3]


def test_sandbox_deployment_profile_has_required_isolation_controls() -> None:
    compose = (ROOT / "infra/compose.yaml").read_text()
    for control in (
        "network_mode: none",
        "read_only: true",
        'user: "65532:65532"',
        'cap_drop: ["ALL"]',
        "pids_limit: 32",
        "mem_limit: 256m",
    ):
        assert control in compose


def test_apparmor_profile_has_an_explicit_installer_and_runtime_toggle() -> None:
    installer = ROOT / "infra/security/install-strategy-sandbox-apparmor.sh"
    assert "apparmor_parser --replace" in installer.read_text()
    runtime = (
        ROOT / "backend/src/crypto_lab/infrastructure/sandbox/generated_strategy_runtime.py"
    ).read_text()
    assert "self._apparmor_profile is not None" in runtime


@pytest.mark.asyncio
async def test_built_sandbox_image_executes_only_through_the_contained_runner() -> None:
    if not _sandbox_image_available():
        pytest.skip("Docker daemon or prebuilt sandbox image is unavailable")
    runtime = DockerGeneratedStrategyRuntime()
    passed, output = await runtime._run_container(
        "def analyze(payload):\n return {'signals': []}\n", {"mode": "self_test"}
    )
    assert passed, output
    assert output == '{"status":"ready"}'


def _sandbox_image_available() -> bool:
    if shutil.which("docker") is None:
        return False
    daemon = subprocess.run(["docker", "info"], capture_output=True, check=False, timeout=5)
    image = subprocess.run(
        ["docker", "image", "inspect", "crypto-lab-strategy-sandbox:1"],
        capture_output=True,
        check=False,
        timeout=5,
    )
    return daemon.returncode == 0 and image.returncode == 0
