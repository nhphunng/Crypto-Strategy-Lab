import ast
from pathlib import Path

SOURCE = Path(__file__).parents[2] / "src" / "crypto_lab"


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_domain_and_application_do_not_import_outer_frameworks() -> None:
    forbidden = {"fastapi", "sqlalchemy", "httpx", "asyncpg", "alembic"}
    for layer in ("domain", "application"):
        for path in (SOURCE / layer).rglob("*.py"):
            assert not (imported_roots(path) & forbidden), path


def test_provider_payload_terms_stay_out_of_domain_application_and_public_schemas() -> None:
    for layer in ("domain", "application"):
        for path in (SOURCE / layer).rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            assert "kline" not in text and "api/v3/klines" not in text, path
    for path in (SOURCE / "api" / "schemas").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        assert "kline" not in text and "api/v3/klines" not in text, path
