from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
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
    provider_connect_timeout_seconds: float = Field(default=3, gt=0, le=30)
    provider_read_timeout_seconds: float = Field(default=10, gt=0, le=60)
    provider_max_attempts: int = Field(default=3, ge=1, le=5)
    provider_max_retry_delay_seconds: int = Field(default=30, ge=1, le=120)
    max_range_candles: int = Field(default=1000, ge=1, le=1000)
    default_range_candles: int = Field(default=500, ge=1, le=1000)
    max_dataset_candles: int = Field(default=10_000, ge=1000, le=1_000_000)
    dataset_build_lease_seconds: int = Field(default=120, ge=10, le=3600)
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

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()
