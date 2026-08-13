# WebSocket Contract: Leaderboard Updates

## Channel

- Endpoint: `GET /ws/v1/leaderboards`
- Client subscribes to validated leaderboard scope(s); server enforces subscription limits.
- REST snapshots remain authoritative. WebSocket events are incremental invalidation/change notifications.

## Subscription Message v1

```json
{
  "eventType": "LEADERBOARD_SUBSCRIBE",
  "version": 1,
  "requestId": "req-...",
  "payload": {
    "scoringPolicyId": "overall",
    "scoringPolicyVersion": "1",
    "rankBy": "OVERALL_SCORE",
    "pair": "BTCUSDT",
    "timeframe": "15m",
    "runId": null,
    "k": 10,
    "lastProjectionVersion": 41
  }
}
```

`scoringPolicyId`, `scoringPolicyVersion`, `rankBy`, and `k` are required and together identify the ranking definition. `pair`, `timeframe`, and `runId` are optional comparison-scope filters matching the REST snapshot query; `k` is `1..200`. Presentation sort, metric-range filters, and pagination are not subscription identity. `lastProjectionVersion` is optional and helps the server/client decide whether an immediate snapshot refetch is required. Invalid/unsupported scopes receive an `ERROR` event and do not create a subscription.

## Event Envelope v1

```json
{
  "eventType": "LEADERBOARD_UPDATED",
  "version": 1,
  "eventId": "018f...",
  "occurredAt": "2026-08-13T03:30:00Z",
  "requestId": "req-...",
  "runId": "run-...",
  "jobId": "job-...",
  "payload": {
    "leaderboardId": "lb-...",
    "scopeKey": "pair:BTCUSDT|timeframe:15m",
    "scoringPolicyId": "overall",
    "scoringPolicyVersion": "1",
    "rankBy": "OVERALL_SCORE",
    "k": 10,
    "projectionVersion": 42,
    "updatedAt": "2026-08-13T03:30:00Z",
    "entryCount": 10,
    "changed": {
      "addedEvaluationResultIds": ["eval-new"],
      "removedEvaluationResultIds": ["eval-old"],
      "movedEvaluationResultIds": ["eval-two"]
    },
    "topOne": {
      "evaluationResultId": "eval-best",
      "strategyId": "ma-rsi-sr",
      "strategyVersion": "3",
      "rank": 1,
      "score": "82.1"
    },
    "runState": "RUNNING"
  }
}
```

## Consumer Rules

1. Deduplicate by `eventId` and by `projectionVersion` within the complete Leaderboard identity (scope, policy/version, `rankBy`, and K).
2. If event version <= current version, ignore it.
3. If event version = current version + 1, invalidate/refetch the matching snapshot (an optimistic changed-set animation is optional).
4. If event version > current version + 1, mark the view stale and immediately refetch the current REST snapshot.
5. On disconnect, keep the last valid snapshot visible with `RECONNECTING`; after reconnect, refetch before declaring `LIVE`.
6. Unknown event `version` or invalid payload must not mutate visible state; log sanitized contract failure and recover via snapshot.

## Producer Rules

- Publish only after the database transaction containing the projection and update record commits. A retryable dispatcher claims durable unpublished records; publication failure never rolls back or repeats the projection change.
- Publication is at least once; duplicate delivery is expected.
- An unchanged or ineligible evaluation does not publish `LEADERBOARD_UPDATED`.
- `eventId`, `projectionVersion`, `runId`, `jobId`, strategy identity, and request correlation propagate into logs/metrics.

## Connection States

`CONNECTING -> LIVE -> RECONNECTING -> LIVE`, or `RECONNECTING -> STALE` after bounded attempts. `STALE` never implies the stored snapshot was deleted.

## Error Events

Protocol-level errors use the same versioned envelope with `eventType: ERROR`; payload contains `code`, `message`, and the originating `requestId`. Codes include `LEADERBOARD_SUBSCRIPTION_INVALID`, `LEADERBOARD_SUBSCRIPTION_LIMITED`, and `LEADERBOARD_EVENT_VERSION_UNSUPPORTED`. Secrets, internal traces, and database details are forbidden.
