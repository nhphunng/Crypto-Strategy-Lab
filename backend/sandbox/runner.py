"""One-shot stdin/stdout adapter executed only inside the generated-strategy sandbox."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "generated_artifact", Path("/sandbox/artifact.py")
    )
    if spec is None or spec.loader is None:
        return 2
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = json.loads(sys.stdin.buffer.read(1_048_577))
    if payload == {"mode": "self_test"}:
        result = (
            {"status": "ready"}
            if callable(getattr(module, "analyze", None))
            else {"status": "invalid"}
        )
    else:
        result = module.analyze(payload)
    encoded = json.dumps(result, separators=(",", ":"), sort_keys=True).encode()
    if len(encoded) > 1_048_576:
        return 3
    sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
