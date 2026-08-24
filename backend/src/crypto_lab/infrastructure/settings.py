from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from crypto_lab.domain.market_data.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    providers: tuple[str, ...] = ("BINANCE",)
    pairs: tuple[str, ...] = ("BTCUSDT",)
    timeframes: tuple[Timeframe, ...] = tuple(Timeframe)

    def validate(self, provider: str, pair: str, timeframe: Timeframe) -> None:
        if provider not in self.providers:
            raise ValueError("MARKET_PROVIDER_UNSUPPORTED")
        if pair not in self.pairs:
            raise ValueError("MARKET_PAIR_UNSUPPORTED")
        if timeframe not in self.timeframes:
            raise ValueError("MARKET_TIMEFRAME_UNSUPPORTED")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CSL_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab"
    binance_base_url: str = "https://api.binance.com"
    binance_websocket_url: str = "wss://stream.binance.com:9443/ws"
    provider_connect_timeout_seconds: float = Field(default=3, gt=0, le=30)
    provider_read_timeout_seconds: float = Field(default=10, gt=0, le=60)
    provider_max_attempts: int = Field(default=3, ge=1, le=5)
    provider_max_retry_delay_seconds: int = Field(default=30, ge=1, le=120)
    provider_heartbeat_interval_seconds: int = Field(default=15, ge=1, le=60)
    provider_stale_after_seconds: int = Field(default=30, ge=2, le=300)
    provider_reconnect_initial_delay_seconds: float = Field(default=1, gt=0, le=30)
    provider_reconnect_max_delay_seconds: float = Field(default=30, gt=0, le=120)
    provider_reconnect_jitter_ratio: float = Field(default=0.2, ge=0, le=0.5)
    provider_reconnect_max_attempts: int = Field(default=8, ge=1, le=8)
    max_range_candles: int = Field(default=1000, ge=1, le=1000)
    default_range_candles: int = Field(default=500, ge=1, le=1000)
    max_dataset_candles: int = Field(default=10_000, ge=1000, le=1_000_000)
    dataset_build_lease_seconds: int = Field(default=120, ge=10, le=3600)
    max_chart_slots_per_connection: int = Field(default=4, ge=1, le=4)
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    log_level: str = "INFO"
    llm_endpoint: str | None = None
    llm_provider: str = "configured-provider"
    llm_model_id: str | None = None
    llm_model_version: str | None = None
    llm_api_key: SecretStr | None = None
    source_encryption_key_base64: SecretStr | None = None
    source_encryption_key_id: str = "local-source-key-v1"
    generated_artifact_root: str = ".data/generated-strategies"
    strategy_sandbox_apparmor_profile: str | None = None

    @field_validator("binance_base_url")
    @classmethod
    def validate_binance_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Binance base URL must be a server-controlled HTTPS URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Binance base URL must not contain credentials, query, or fragment")
        return value.rstrip("/")

    @field_validator("binance_websocket_url")
    @classmethod
    def validate_binance_websocket_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "wss" or not parsed.hostname:
            raise ValueError("Binance WebSocket URL must be a server-controlled WSS URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "Binance WebSocket URL must not contain credentials, query, or fragment"
            )
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_realtime_bounds(self) -> Settings:
        if self.provider_stale_after_seconds <= self.provider_heartbeat_interval_seconds:
            raise ValueError("provider stale timeout must exceed the heartbeat interval")
        if (
            self.provider_reconnect_max_delay_seconds
            < self.provider_reconnect_initial_delay_seconds
        ):
            raise ValueError("reconnect max delay must not be below the initial delay")
        return self

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()
