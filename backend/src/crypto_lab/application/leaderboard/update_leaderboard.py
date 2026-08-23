"""Transactional Top-K maintenance driven by completed Evaluation Results.

This use case consumes immutable upstream evaluations and scores. It never
recomputes a financial metric, generates a Signal, or simulates a Trade.
"""

from __future__ import annotations

from uuid import UUID

from crypto_lab.application.leaderboard.errors import query_invalid
from crypto_lab.application.leaderboard.ports import (
    Clock,
    LeaderboardRepository,
    ProjectionOutcome,
    Recompute,
    UpdateSource,
)
from crypto_lab.domain.leaderboard.entry import RankableCandidate
from crypto_lab.domain.leaderboard.policy import (
    LeaderboardIdentity,
    ProjectionVersion,
    ScoringPolicy,
)
from crypto_lab.domain.leaderboard.ranking import RankingOutcome, rank_candidates


class UpdateLeaderboard:
    """Recompute one or more projections from authoritative inputs, idempotently."""

    def __init__(self, repository: LeaderboardRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def for_identity(
        self,
        identity: LeaderboardIdentity,
        *,
        source: UpdateSource | None = None,
    ) -> ProjectionOutcome:
        policy = await self._load_policy(identity)
        return await self._repository.mutate_projection(
            identity,
            _recompute_with(policy, identity),
            now=self._clock.now(),
            source=source,
        )

    async def for_evaluation(
        self,
        evaluation_result_id: UUID,
        *,
        request_id: str | None = None,
    ) -> tuple[ProjectionOutcome, ...]:
        """Refresh every projection whose comparison scope contains the evaluation.

        Duplicate delivery is harmless: recomputation from the same immutable
        inputs produces an identical ordering and therefore no visible change.
        """

        identities = await self._repository.find_identities_for_evaluation(evaluation_result_id)
        outcomes: list[ProjectionOutcome] = []
        for identity in identities:
            source = UpdateSource(
                evaluation_result_id=evaluation_result_id,
                request_id=request_id,
            )
            outcomes.append(await self.for_identity(identity, source=source))
        return tuple(outcomes)

    async def _load_policy(self, identity: LeaderboardIdentity) -> ScoringPolicy:
        policy = await self._repository.load_policy(identity.policy)
        if policy is None:
            raise query_invalid(
                "The requested scoring policy version is unknown.",
                scoringPolicyId=identity.policy.policy_id,
                scoringPolicyVersion=identity.policy.version,
            )
        return policy


def _recompute_with(policy: ScoringPolicy, identity: LeaderboardIdentity) -> Recompute:
    def recompute(
        candidates: tuple[RankableCandidate, ...],
        version: ProjectionVersion,
    ) -> RankingOutcome:
        return rank_candidates(
            candidates,
            policy=policy,
            rank_metric=identity.rank_metric,
            k=identity.k,
            projection_version=version,
        )

    return recompute
