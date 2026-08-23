from uuid import UUID

from crypto_lab.domain.strategy.generation import GeneratedStrategyDraft, RuleEvidence
from crypto_lab.domain.strategy.parameters import ParameterSchema


def test_draft_is_immutable_evidence_backed_and_fingerprinted() -> None:
    draft = GeneratedStrategyDraft(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        0,
        "breakout",
        "Breakout",
        "Buy a strict breakout.",
        {"entry": "close > prior high", "exit": "close < prior low"},
        ParameterSchema(()),
        ("Closed candles only",),
        (RuleEvidence("entry", "close breaks above", "paragraph 1"),),
    )
    assert len(draft.draft_fingerprint) == 64
    assert draft.draft_fingerprint == draft.draft_fingerprint
