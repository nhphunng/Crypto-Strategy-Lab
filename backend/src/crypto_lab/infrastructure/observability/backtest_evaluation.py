from __future__ import annotations

import logging
from collections.abc import Mapping

logger = logging.getLogger("crypto_lab.backtest_evaluation")

_ALLOWED_FIELDS = {
    "backtest_result_id",
    "duration_ms",
    "evaluation_result_id",
    "failure_code",
    "job_id",
    "request_id",
    "result_checksum",
    "run_id",
}


def record_event(name: str, fields: Mapping[str, object]) -> None:
    """Emit bounded Feature 004 telemetry without request bodies or credentials."""
    safe = {key: value for key, value in fields.items() if key in _ALLOWED_FIELDS}
    logger.info(name, extra={"fields": safe})
