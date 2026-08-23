from pathlib import Path

from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    ALLOWED_IMPORTS,
    FORBIDDEN_CALLS,
)

ROOT = Path(__file__).parents[3]


def test_generated_security_policy_is_enforced_by_runtime_and_deployment() -> None:
    assert {"math", "decimal", "statistics", "strategy_sdk"} == set(ALLOWED_IMPORTS)
    assert {"eval", "exec", "compile", "open", "__import__"} <= set(FORBIDDEN_CALLS)
    compose = (ROOT / "infra/compose.yaml").read_text()
    for requirement in (
        "network_mode: none",
        "read_only: true",
        "no-new-privileges:true",
        "apparmor=crypto-lab-strategy-sandbox",
        "pids_limit: 32",
    ):
        assert requirement in compose


def test_frontend_carries_analytical_disclaimer_and_explicit_confirmation() -> None:
    form = (
        ROOT / "frontend/src/features/strategies/components/StrategyGenerationForm.tsx"
    ).read_text()
    review = (
        ROOT / "frontend/src/features/strategies/components/GeneratedStrategyReview.tsx"
    ).read_text()
    assert "Analytical use only" in form
    assert "I reviewed these exact rules" in review
    assert "confirmed" in review
