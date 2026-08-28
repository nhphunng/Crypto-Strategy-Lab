from __future__ import annotations

import ast
from pathlib import Path


def test_domain_has_no_framework_dependencies_or_concrete_strategy_branches() -> None:
    root = Path(__file__).parents[2] / "src" / "crypto_lab" / "domain"
    feature_files = tuple((root / "backtest").glob("*.py")) + tuple(
        (root / "evaluation").glob("*.py")
    )
    forbidden_imports = {"fastapi", "sqlalchemy", "pydantic"}
    for path in feature_files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        } | {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert not imports & forbidden_imports, path
    engine = (root / "backtest" / "engine.py").read_text(encoding="utf-8").lower()
    assert "moving_average" not in engine
    assert "rsistrategy" not in engine
