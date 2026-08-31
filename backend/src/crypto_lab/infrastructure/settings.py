from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from crypto_lab.domain.market_data.timeframe import Timeframe


class NewsFeedConfig(PydanticBaseModel):
    """A server-controlled HTTPS RSS/Atom feed to collect from."""

    source: str
    url: str

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("news feed source must not be blank")
        return normalized

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("news feed URL must be a server-controlled HTTPS URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "news feed URL must not contain credentials, query, or fragment"
            )
        return value.rstrip("/")



@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    providers: tuple[str, ...] = ("BINANCE",)
    pairs: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
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
    # Off by default so tests and local runs never reach the provider on
    # startup; the shipped Compose deployment turns it on.
    auto_evaluation_enabled: bool = False
    auto_evaluation_pair: str = "BTCUSDT"
    auto_evaluation_timeframe: str = "15m"
    auto_evaluation_candles: int = Field(default=500, ge=50, le=5000)
    auto_evaluation_interval_seconds: float = Field(default=3600, ge=60, le=86_400)
    # News collection is off by default so tests and local runs never reach a
    # feed on startup; the shipped Compose deployment turns it on.
    news_collection_enabled: bool = False
    news_collection_interval_seconds: float = Field(default=900, ge=60, le=86_400)
    news_feeds: tuple[NewsFeedConfig, ...] = (
        NewsFeedConfig(source="Cointelegraph", url="https://cointelegraph.com/rss"),
    )
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
    llm_data_policy_confirmed: bool = False
    llm_connect_timeout_seconds: float = Field(default=5, gt=0, le=30)
    llm_read_timeout_seconds: float = Field(default=30, gt=0, le=120)
    llm_max_attempts: int = Field(default=3, ge=1, le=5)
    llm_max_retry_delay_seconds: float = Field(default=30, gt=0, le=120)
    source_encryption_key_base64: SecretStr | None = None
    source_encryption_key_id: str = "local-source-key-v1"
    generated_artifact_root: str = ".data/generated-strategies"
    strategy_sandbox_image: str = Field(default="crypto-lab-strategy-sandbox:1", min_length=1)
    strategy_sandbox_apparmor_profile: str | None = None
    strategy_sandbox_engine_url: str | None = None

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

    @field_validator("llm_api_key", "source_encryption_key_base64")
    @classmethod
    def validate_non_empty_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("configured secret must not be empty")
        return value

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

    @model_validator(mode="after")
    def validate_generation_configuration(self) -> Settings:
        llm_configuration = (
            self.llm_endpoint,
            self.llm_model_id,
            self.llm_model_version,
            self.llm_api_key,
        )
        if any(llm_configuration) and not all(llm_configuration):
            raise ValueError("LLM generation configuration must be complete")
        if all(llm_configuration) and self.source_encryption_key_base64 is None:
            raise ValueError("LLM generation requires encrypted artifact storage")
        if all(llm_configuration) and not self.llm_data_policy_confirmed:
            raise ValueError("live generation requires explicit LLM data-policy confirmation")
        return self

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()
