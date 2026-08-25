import asyncio
import json
import shutil
import subprocess
import time
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


@pytest.mark.asyncio
async def test_built_sandbox_image_enforces_runtime_containment_controls() -> None:
    if not _sandbox_image_available():
        pytest.skip("Docker daemon or prebuilt sandbox image is unavailable")
    runtime = DockerGeneratedStrategyRuntime()
    passed, output = await runtime._run_container(_containment_probe(), {"mode": "probe"})
    assert passed, output
    probe = json.loads(output)["probe"]
    assert probe == {
        "capabilities": "0000000000000000",
        "cslEnvironment": [],
        "memoryLimit": "268435456",
        "networkBlocked": True,
        "noNewPrivileges": "1",
        "pidsLimit": "32",
        "processBlocked": True,
        "rootFilesystemBlocked": True,
        "uid": 65532,
    }


@pytest.mark.asyncio
async def test_built_sandbox_terminates_unbounded_artifacts_without_leaking_containers() -> None:
    if not _sandbox_image_available():
        pytest.skip("Docker daemon or prebuilt sandbox image is unavailable")
    runtime = DockerGeneratedStrategyRuntime()
    started = time.monotonic()
    passed, output = await runtime._run_container("while True:\n pass\n", {"mode": "self_test"})
    assert not passed
    assert output == "isolated runtime unavailable or timed out"
    assert time.monotonic() - started < 8
    leaked = await asyncio.create_subprocess_exec(
        "docker",
        "ps",
        "-aq",
        "--filter",
        "name=crypto-lab-strategy-",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await leaked.communicate()
    assert leaked.returncode == 0
    assert stdout.strip() == b""


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


def _containment_probe() -> str:
    return '''
def analyze(payload):
    import os
    import socket

    def blocked(operation):
        try:
            operation()
        except OSError:
            return True
        return False

    status = {}
    with open("/proc/self/status", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("CapEff:"):
                status["capabilities"] = line.split()[1]
            elif line.startswith("NoNewPrivs:"):
                status["noNewPrivileges"] = line.split()[1]
    with open("/sys/fs/cgroup/memory.max", encoding="utf-8") as stream:
        status["memoryLimit"] = stream.read().strip()
    with open("/sys/fs/cgroup/pids.max", encoding="utf-8") as stream:
        status["pidsLimit"] = stream.read().strip()
    status.update({
        "uid": os.getuid(),
        "cslEnvironment": sorted(key for key in os.environ if key.startswith("CSL_")),
        "networkBlocked": blocked(lambda: socket.socket()),
        "rootFilesystemBlocked": blocked(lambda: open("/runner/probe", "w")),
        "processBlocked": blocked(lambda: os.fork()),
    })
    return {"signals": [], "probe": status}
'''
