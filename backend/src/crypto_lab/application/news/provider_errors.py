"""Typed errors raised by news provider adapters (transport/parse failures)."""

from __future__ import annotations


class NewsProviderError(Exception):
    """Typed base for failures while collecting a news feed."""


class NewsTransportError(NewsProviderError):
    """The feed URL could not be fetched over the HTTP transport."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"[{source}] {message}")
        self.source = source


class NewsFeedParseError(NewsProviderError):
    """The feed document is not valid, parseable RSS/Atom."""

    def __init__(self, source: str) -> None:
        super().__init__(f"[{source}] feed document is not valid RSS/Atom")
        self.source = source


__all__ = ["NewsFeedParseError", "NewsProviderError", "NewsTransportError"]
