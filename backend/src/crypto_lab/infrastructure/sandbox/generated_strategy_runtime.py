from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from crypto_lab.domain.strategy.errors import ErrorIssue
from crypto_lab.domain.strategy.generation import (
    GeneratedStrategyArtifact,
    StrategyValidationReport,
    ValidationCheck,
    ValidationStatus,
)

ALLOWED_IMPORTS = frozenset({"math", "decimal", "statistics", "strategy_sdk"})
FORBIDDEN_CALLS = frozenset({"eval", "exec", "compile", "open", "__import__", "input"})


class DockerGeneratedStrategyRuntime:
    """Validate model-authored code statically and only run it in the approved container."""

    policy_version = "generated-strategy-validation-v1"

    def __init__(
        self,
        image: str = "crypto-lab-strategy-sandbox:1",
        apparmor_profile: str | None = None,
    ) -> None:
        self._image = image
        self._apparmor_profile = apparmor_profile

    async def validate(self, artifact: GeneratedStrategyArtifact) -> StrategyValidationReport:
        started = datetime.now(UTC)
        checks, findings = _static_checks(artifact.source_code, artifact.declared_imports)
        if all(item.passed for item in checks):
            passed, message = await self._run_container(artifact.source_code, {"mode": "self_test"})
            checks += (ValidationCheck("isolated_contract_fixtures", passed, message),)
        if all(item.passed for item in checks):
            checks += await self._behavior_checks(artifact.source_code)
        status = (
            ValidationStatus.PASSED
            if all(item.passed for item in checks)
            else ValidationStatus.FAILED
        )
        return StrategyValidationReport(
            uuid4(),
            artifact.id,
            artifact.content_fingerprint,
            self.policy_version,
            status,
            checks,
            findings,
            started,
            datetime.now(UTC),
            hashlib.sha256(self._image.encode()).hexdigest(),
        )

    async def _behavior_checks(self, source_code: str) -> tuple[ValidationCheck, ...]:
        prefix = _fixture_payload(3)
        extended = _fixture_payload(4)
        first_ok, first = await self._run_container(source_code, prefix)
        second_ok, second = await self._run_container(source_code, prefix)
        extended_ok, future = await self._run_container(source_code, extended)
        schema_ok = first_ok and _valid_signal_payload(first, expected_count=3)
        deterministic = first_ok and second_ok and first == second
        no_look_ahead = False
        if schema_ok and extended_ok and _valid_signal_payload(future, expected_count=4):
            no_look_ahead = json.loads(first)["signals"] == json.loads(future)["signals"][:3]
        bounded = first_ok and second_ok and extended_ok
        return (
            ValidationCheck(
                "contract_schema",
                schema_ok,
                "signal contract accepted" if schema_ok else "signal contract rejected",
            ),
            ValidationCheck(
                "determinism",
                deterministic,
                "repeat output matched" if deterministic else "repeat output differed",
            ),
            ValidationCheck(
                "no_look_ahead",
                no_look_ahead,
                "prefix output stable" if no_look_ahead else "future candle changed prefix output",
            ),
            ValidationCheck(
                "resource_bounds",
                bounded,
                "all bounded runs completed" if bounded else "bounded run failed",
            ),
            ValidationCheck(
                "host_provenance_projection",
                schema_ok,
                "host can assign exact candle timestamps, sequence positions, and provenance"
                if schema_ok
                else "raw signals cannot be projected into the common provenance contract",
            ),
        )

    async def execute(self, source_code: str, payload: dict[str, object]) -> dict[str, object]:
        passed, output = await self._run_container(source_code, payload)
        if not passed:
            raise RuntimeError(output)
        parsed = json.loads(output)
        if not isinstance(parsed, dict):
            raise RuntimeError("sandbox returned a non-object result")
        return parsed

    async def _run_container(
        self, source_code: str, payload: dict[str, object]
    ) -> tuple[bool, str]:
        project_root = Path(__file__).parents[5]
        seccomp_profile = project_root / "infra/security/strategy-sandbox-seccomp.json"
        container_name = f"crypto-lab-strategy-{uuid4().hex}"
        with tempfile.TemporaryDirectory(prefix="crypto-lab-strategy-") as directory:
            artifact_path = Path(directory) / "artifact.py"
            artifact_path.write_text(source_code, encoding="utf-8")
            command = [
                "docker",
                "run",
                "--rm",
                "--interactive",
                "--name",
                container_name,
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--security-opt",
                f"seccomp={seccomp_profile}",
                "--pids-limit=32",
                "--cpus=1",
                "--memory=256m",
                "--memory-swap=256m",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                "--user=65532:65532",
                "--mount",
                f"type=bind,src={artifact_path},dst=/sandbox/artifact.py,readonly",
            ]
            if self._apparmor_profile is not None:
                command += ["--security-opt", f"apparmor={self._apparmor_profile}"]
            command.append(self._image)
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(json.dumps(payload).encode()), timeout=5
                )
            except FileNotFoundError:
                return False, "isolated runtime unavailable or timed out"
            except TimeoutError:
                process.kill()
                await process.communicate()
                await _force_remove_container(container_name)
                return False, "isolated runtime unavailable or timed out"
            if len(stdout) > 1_048_576:
                return False, "sandbox output exceeded 1 MiB"
            if process.returncode != 0:
                return False, stderr.decode(errors="replace")[:1000]
            return True, stdout.decode()


async def _force_remove_container(container_name: str) -> None:
    try:
        cleanup = await asyncio.create_subprocess_exec(
            "docker",
            "rm",
            "--force",
            container_name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(cleanup.wait(), timeout=2)
    except (FileNotFoundError, TimeoutError):
        return


def _static_checks(
    source_code: str, declared_imports: frozenset[str] | None = None
) -> tuple[tuple[ValidationCheck, ...], tuple[ErrorIssue, ...]]:
    checks = []
    findings: list[ErrorIssue] = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError as error:
        return (
            (ValidationCheck("python_syntax", False, "artifact is not valid Python"),),
            (ErrorIssue("sourceCode", "SYNTAX", f"line {error.lineno}"),),
        )
    imports: set[str] = set()
    forbidden: list[str] = []
    has_entrypoint = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FORBIDDEN_CALLS
        ):
            forbidden.append(node.func.id)
        elif isinstance(node, ast.FunctionDef) and node.name == "analyze":
            has_entrypoint = True
    denied = sorted(imports - ALLOWED_IMPORTS)
    declaration_matches = declared_imports is None or imports == set(declared_imports)
    checks.append(ValidationCheck("python_syntax", True, "syntax accepted"))
    checks.append(
        ValidationCheck(
            "import_allowlist",
            not denied,
            "accepted" if not denied else f"denied: {', '.join(denied)}",
        )
    )
    checks.append(
        ValidationCheck(
            "declared_imports",
            declaration_matches,
            "actual imports match artifact metadata"
            if declaration_matches
            else "actual imports differ from artifact metadata",
        )
    )
    if not declaration_matches:
        findings.append(
            ErrorIssue("declaredImports", "IMPORT_METADATA_MISMATCH", "imports must match exactly")
        )
    checks.append(
        ValidationCheck(
            "forbidden_builtins",
            not forbidden,
            "accepted" if not forbidden else "forbidden dynamic or I/O call",
        )
    )
    checks.append(
        ValidationCheck(
            "contract_entrypoint",
            has_entrypoint,
            "analyze entrypoint present" if has_entrypoint else "analyze entrypoint missing",
        )
    )
    return tuple(checks), tuple(findings)


def _fixture_payload(count: int) -> dict[str, object]:
    return {
        "contractVersion": "1.0.0",
        "parameters": {},
        "context": {
            "datasetId": "validation-fixture",
            "datasetVersion": "v1",
            "decisionTimestamp": "2026-01-01T04:00:00.000Z",
            "candles": [
                {
                    "timestamp": f"2026-01-01T0{index}:00:00.000Z",
                    "open": str(100 + index),
                    "high": str(101 + index),
                    "low": str(99 + index),
                    "close": str(100 + index),
                    "volume": "1",
                }
                for index in range(count)
            ],
        },
    }


def _valid_signal_payload(raw: str, *, expected_count: int) -> bool:
    try:
        parsed = json.loads(raw)
        signals = parsed["signals"]
        return (
            isinstance(signals, list)
            and len(signals) == expected_count
            and all(
                isinstance(item, dict)
                and item.get("action") in {"BUY", "SELL", "HOLD"}
                and item.get("phase") in {"WARMUP", "EVALUATED"}
                and ("sequence" not in item or item["sequence"] == index)
                and (
                    "timestamp" not in item
                    or item["timestamp"] == f"2026-01-01T0{index}:00:00.000Z"
                )
                for index, item in enumerate(signals)
            )
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
