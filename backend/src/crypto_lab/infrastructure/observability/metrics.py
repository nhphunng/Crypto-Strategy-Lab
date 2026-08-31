"""In-process market-data stream metrics.

The channel records sanitized counters and gauges here. There is no external
metrics platform in scope: structured logs plus these counters satisfy the
feature observability contract, and `snapshot` allows future exposition.
"""

from __future__ import annotations

from typing import Any


class MarketDataMetrics:
    """Connection-scoped and aggregate stream counters.

    A shared instance aggregates across channels; tests pass a private
    instance to assert channel behavior in isolation.
    """

    def __init__(self) -> None:
        self.clients_connected = 0
        self.logical_slots = 0
        self.unique_selections = 0
        self.reconnects = 0
        self.recovery_failures = 0
        self.invalid_events = 0
        self.last_event_age_seconds: float | None = None
        self.publish_latency_ms_count = 0
        self.publish_latency_ms_total = 0
        self.publish_latency_ms_max = 0

    def record_publish_latency_ms(self, duration_ms: int) -> None:
        self.publish_latency_ms_count += 1
        self.publish_latency_ms_total += duration_ms
        self.publish_latency_ms_max = max(self.publish_latency_ms_max, duration_ms)

    def snapshot(self) -> dict[str, Any]:
        return {
            "clientsConnected": self.clients_connected,
            "logicalSlots": self.logical_slots,
            "uniqueSelections": self.unique_selections,
            "reconnects": self.reconnects,
            "recoveryFailures": self.recovery_failures,
            "invalidEvents": self.invalid_events,
            "lastEventAgeSeconds": self.last_event_age_seconds,
            "publishLatencyMs": {
                "count": self.publish_latency_ms_count,
                "total": self.publish_latency_ms_total,
                "max": self.publish_latency_ms_max,
            },
        }
