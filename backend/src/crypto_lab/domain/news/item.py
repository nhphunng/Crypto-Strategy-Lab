from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID


@dataclass(frozen=True, slots=True)
class NewsItem:
    id: UUID
    provider: str
    provider_item_id: str
    title: str
    content: str
    source: str
    published_at: datetime
    crawled_at: datetime
    related_coins: tuple[str, ...]
    url: str
    canonical_url: str
    content_fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        for field_name in ("provider", "provider_item_id", "title", "content", "source"):
            normalized = " ".join(getattr(self, field_name).split())
            if not normalized:
                raise ValueError(f"{field_name} must not be blank")
            object.__setattr__(self, field_name, normalized)
        for field_name in ("url", "canonical_url"):
            value = getattr(self, field_name).strip()
            parsed = urlsplit(value)
            if parsed.scheme.lower() != "https" or not parsed.netloc:
                raise ValueError(f"{field_name} must be an HTTPS URL")
            object.__setattr__(self, field_name, value)
        normalized_coins = {coin.strip().upper() for coin in self.related_coins}
        object.__setattr__(self, "related_coins", tuple(sorted(normalized_coins)))
        for field_name in ("published_at", "crawled_at"):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
            object.__setattr__(self, field_name, value.astimezone(UTC))
        if self.published_at > self.crawled_at:
            raise ValueError("published_at must not be after crawled_at")

        fingerprint_input = "\n".join((self.title, self.content, self.canonical_url))
        object.__setattr__(
            self,
            "content_fingerprint",
            hashlib.sha256(fingerprint_input.encode()).hexdigest(),
        )
