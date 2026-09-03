#!/usr/bin/env python3
"""Prepare Compose secret files without printing or exporting their values."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

SECRET_SPECS = (
    (
        "CSL_LLM_API_KEY_HOST_FILE",
        ".runtime-secrets/llm_api_key",
        "CSL_LLM_API_KEY",
    ),
    (
        "CSL_SOURCE_ENCRYPTION_KEY_HOST_FILE",
        ".runtime-secrets/source_encryption_key",
        "CSL_SOURCE_ENCRYPTION_KEY_BASE64",
    ),
)


def _dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _secure_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


def _write_secret(path: Path, value: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing to replace symlinked secret file: {path}")
    _secure_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.write("\n")
        temporary.chmod(0o444)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(project_root: Path, env_file: Path) -> None:
    values = _dotenv(env_file)
    missing: list[str] = []
    for path_key, default_path, legacy_value_key in SECRET_SPECS:
        configured_path = Path(values.get(path_key, default_path))
        target = (
            configured_path
            if configured_path.is_absolute()
            else project_root / configured_path
        )
        managed_target = project_root / default_path
        if target.is_file() and target.stat().st_size > 0:
            if target.is_symlink():
                raise RuntimeError(f"refusing to use symlinked secret file: {target}")
            if target == managed_target:
                _secure_directory(target.parent)
            elif target.parent.stat().st_mode & 0o077:
                raise RuntimeError(f"secret directory must have mode 0700: {target.parent}")
            target.chmod(0o444)
            continue
        legacy_value = values.get(legacy_value_key, "").strip()
        if not legacy_value:
            missing.append(f"{target} (or legacy {legacy_value_key})")
            continue
        if target != managed_target:
            missing.append(f"operator-managed secret file {target}")
            continue
        _write_secret(target, legacy_value)
    if missing:
        raise RuntimeError("missing production secret source: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--env-file", type=Path, default=Path(".env.production"))
    arguments = parser.parse_args()
    project_root = arguments.project_root.resolve()
    env_file = arguments.env_file
    if not env_file.is_absolute():
        env_file = project_root / env_file
    prepare(project_root, env_file)
    print("Production secret files are ready.")


if __name__ == "__main__":
    main()
