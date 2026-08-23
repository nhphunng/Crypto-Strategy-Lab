import ast
from pathlib import Path

ROOT = Path(__file__).parents[2] / "src/crypto_lab/domain/strategy"
FORBIDDEN_IMPORTS = {
    "sqlalchemy",
    "fastapi",
    "httpx",
    "asyncpg",
    "os",
    "random",
    "subprocess",
    "pathlib",
}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__"}


def test_strategy_calculation_has_no_ambient_io_clock_randomness_or_process_access() -> None:
    files = [ROOT / "context.py", *(ROOT / "implementations").glob("*.py")]
    violations = []
    for path in files:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                module = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                if (module or "").split(".")[0] in FORBIDDEN_IMPORTS:
                    violations.append(f"{path.name}: import {module}")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_CALLS
            ):
                violations.append(f"{path.name}: call {node.func.id}")
    assert violations == []
