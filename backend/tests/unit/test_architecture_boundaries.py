from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

DOMAIN_ROOT = Path(__file__).parents[2] / "src" / "crypto_lab" / "domain"

# These packages belong to delivery, persistence, or provider-adapter layers.  Keeping the
# list here (instead of importing them) also means this guard works when an optional provider
# SDK is not installed in the test environment.
FORBIDDEN_EXTERNAL_IMPORTS: dict[str, str] = {
    "fastapi": "FastAPI delivery framework",
    "sqlalchemy": "SQLAlchemy persistence framework",
    "binance": "Binance provider SDK",
    "ccxt": "CCXT provider SDK",
    "coinbase": "Coinbase provider SDK",
    "krakenex": "Kraken provider SDK",
    "websocket": "WebSocket client",
    "websockets": "WebSocket client",
    "aiohttp": "HTTP/WebSocket client",
    "httpx": "HTTP provider client",
}
FORBIDDEN_PROJECT_IMPORTS: dict[str, str] = {
    "crypto_lab.api": "API delivery layer",
    "crypto_lab.infrastructure": "infrastructure/provider layer",
}
FORBIDDEN_RELATIVE_ROOTS: dict[str, str] = {
    "api": "API delivery layer",
    "infrastructure": "infrastructure/provider layer",
}


def _declared_imports(path: Path) -> Iterable[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            relative_prefix = "." * node.level
            if node.module:
                yield from (f"{relative_prefix}{node.module}.{alias.name}" for alias in node.names)
            else:
                yield from (f"{relative_prefix}{alias.name}" for alias in node.names)


def _boundary_violation(module: str) -> str | None:
    normalized = module.lstrip(".")
    for prefix, reason in FORBIDDEN_EXTERNAL_IMPORTS.items():
        if normalized == prefix or normalized.startswith(f"{prefix}."):
            return reason
    for prefix, reason in FORBIDDEN_PROJECT_IMPORTS.items():
        if normalized == prefix or normalized.startswith(f"{prefix}."):
            return reason
    if module.startswith("."):
        relative_root = normalized.split(".", maxsplit=1)[0]
        return FORBIDDEN_RELATIVE_ROOTS.get(relative_root)
    return None


def test_domain_does_not_import_frameworks_provider_sdks_or_transport_clients() -> None:
    violations: list[str] = []

    for path in sorted(DOMAIN_ROOT.rglob("*.py")):
        for imported_module in _declared_imports(path):
            if reason := _boundary_violation(imported_module):
                relative_path = path.relative_to(DOMAIN_ROOT.parent.parent)
                violations.append(f"{relative_path}: {imported_module} ({reason})")

    assert violations == [], "Domain import boundary violations:\n" + "\n".join(violations)
