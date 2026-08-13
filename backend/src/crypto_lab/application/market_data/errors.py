from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorDescriptor:
    code: str
    message: str
    retryable: bool = False
    details: Mapping[str, Any] | None = None
    retry_after_seconds: int | None = None


class MarketDataError(Exception):
    def __init__(self, descriptor: ErrorDescriptor) -> None:
        super().__init__(descriptor.message)
        self.descriptor = descriptor


class CandleConflictError(MarketDataError):
    def __init__(self) -> None:
        super().__init__(
            ErrorDescriptor(
                "MARKET_CANDLE_CONFLICT",
                "Stored historical Candle conflicts with the provider value.",
            )
        )


class DatasetIntegrityError(MarketDataError):
    def __init__(self) -> None:
        super().__init__(
            ErrorDescriptor(
                "MARKET_DATASET_INTEGRITY_FAILED",
                "The immutable dataset failed integrity validation.",
            )
        )


class ProviderError(MarketDataError):
    pass


class ProviderRateLimited(ProviderError):
    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__(
            ErrorDescriptor(
                "PROVIDER_RATE_LIMITED",
                "The market-data provider rate limit was reached.",
                retryable=True,
                retry_after_seconds=retry_after_seconds,
            )
        )


class ProviderUnavailable(ProviderError):
    def __init__(self) -> None:
        super().__init__(
            ErrorDescriptor(
                "MARKET_PROVIDER_UNAVAILABLE",
                "The market-data provider is temporarily unavailable.",
                retryable=True,
            )
        )


class ProviderPayloadInvalid(ProviderError):
    def __init__(self) -> None:
        super().__init__(
            ErrorDescriptor(
                "MARKET_PROVIDER_PAYLOAD_INVALID",
                "The market-data provider returned an invalid payload.",
            )
        )


def invalid_request(code: str, message: str, **details: Any) -> MarketDataError:
    return MarketDataError(ErrorDescriptor(code, message, details=details or None))
