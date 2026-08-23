from __future__ import annotations

import asyncio
import ipaddress
import socket
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import UUID, uuid4, uuid5

import httpx

from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError
from crypto_lab.domain.strategy.generation import GenerationSourceType
from crypto_lab.domain.strategy.provenance import RetentionClass, StrategySourceSnapshot

MAX_TRANSFER_BYTES = 5_242_880
MAX_SOURCE_BYTES = 1_048_576
MAX_REDIRECTS = 3
ALLOWED_MEDIA_TYPES = frozenset({"text/html", "text/plain"})


class SafeWebSourceAdapter:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def prepare(self, url: str, request_id: str) -> tuple[StrategySourceSnapshot, str]:
        current = _canonical_url(url)
        for redirect in range(MAX_REDIRECTS + 1):
            addresses = await _public_destinations(current)
            hostname = urlsplit(current).hostname
            assert hostname is not None
            pinned = _url_with_destination(current, addresses[0])
            try:
                request = self._client.build_request(
                    "GET",
                    pinned,
                    headers={
                        "Accept": "text/html,text/plain",
                        "Host": hostname,
                        "User-Agent": "CryptoStrategyLab-SourceReader/1.0",
                        "X-Request-ID": request_id,
                    },
                    timeout=httpx.Timeout(10, connect=3),
                    extensions={"sni_hostname": hostname.encode("ascii")},
                )
                response = await self._client.send(request, stream=True, follow_redirects=False)
            except httpx.HTTPError as error:
                raise StrategyError(
                    ErrorCategory.SOURCE_UNAVAILABLE, "permitted webpage could not be retrieved"
                ) from error
            if response.is_redirect:
                try:
                    if redirect == MAX_REDIRECTS or "location" not in response.headers:
                        raise _denied("redirect", "redirect limit or location is invalid")
                    current = _canonical_url(urljoin(current, response.headers["location"]))
                finally:
                    await response.aclose()
                continue
            try:
                if response.status_code != 200:
                    raise StrategyError(
                        ErrorCategory.SOURCE_UNAVAILABLE,
                        f"permitted webpage returned HTTP {response.status_code}",
                    )
                media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if media_type not in ALLOWED_MEDIA_TYPES:
                    raise _denied("mediaType", "source media type is not allowed")
                declared = response.headers.get("content-length")
                if declared is not None and int(declared) > MAX_TRANSFER_BYTES:
                    raise _denied("size", "source exceeds the five MiB transfer limit")
                chunks: list[bytes] = []
                transferred = 0
                async for chunk in response.aiter_bytes():
                    transferred += len(chunk)
                    if transferred > MAX_TRANSFER_BYTES:
                        raise _denied("size", "source exceeds the five MiB transfer limit")
                    chunks.append(chunk)
                content = b"".join(chunks)
            finally:
                await response.aclose()
            try:
                decoded = content.decode(response.encoding or "utf-8", errors="strict")
            except (UnicodeDecodeError, LookupError) as error:
                raise StrategyError(
                    ErrorCategory.SOURCE_UNAVAILABLE, "source text encoding is invalid"
                ) from error
            inert = _extract_inert_text(decoded, media_type)
            if len(inert.encode("utf-8")) > MAX_SOURCE_BYTES:
                raise _denied("size", "decoded source exceeds the one MiB content limit")
            if not inert:
                raise StrategyError(ErrorCategory.SOURCE_UNAVAILABLE, "source has no usable text")
            now = datetime.now(UTC)
            snapshot = StrategySourceSnapshot(
                id=_snapshot_id(request_id),
                source_type=GenerationSourceType.WEBPAGE_URL,
                submitted_url=url,
                canonical_url=current,
                retrieved_at=now,
                content_fingerprint=StrategySourceSnapshot.fingerprint(inert),
                media_type=media_type,
                size=len(content),
                access_policy_version="source-access-v1",
                retention_class=RetentionClass.FINGERPRINT_ONLY,
                attribution=current,
            )
            return snapshot, inert
        raise _denied("redirect", "redirect limit exceeded")


def _canonical_url(value: str) -> str:
    if len(value) > 2048:
        raise _denied("url", "URL is too long")
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise _denied("url", "only absolute HTTPS URLs are allowed")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise _denied("url", "credentials and non-443 ports are prohibited")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    netloc = host if parsed.port is None else f"{host}:443"
    return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))


async def _public_destinations(
    url: str,
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    hostname = urlsplit(url).hostname
    assert hostname is not None
    addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]
    try:
        direct = ipaddress.ip_address(hostname)
        addresses = (direct,)
    except ValueError:
        loop = asyncio.get_running_loop()
        try:
            records = await loop.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        except socket.gaierror as error:
            raise StrategyError(
                ErrorCategory.SOURCE_UNAVAILABLE, "source DNS resolution failed"
            ) from error
        addresses = tuple(ipaddress.ip_address(item[4][0]) for item in records)
    if not addresses or any(not address.is_global for address in addresses):
        raise _denied("destination", "source resolves to a non-public destination")
    return tuple(sorted(set(addresses), key=lambda item: (item.version, int(item))))


def _url_with_destination(url: str, address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    parsed = urlsplit(url)
    host = f"[{address}]" if address.version == 6 else str(address)
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, ""))


def _snapshot_id(request_id: str) -> UUID:
    try:
        return uuid5(UUID(request_id), "source")
    except ValueError:
        return uuid4()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth and data.strip():
            self.parts.append(data.strip())


def _extract_inert_text(content: str, media_type: str) -> str:
    if media_type == "text/plain":
        return "\n".join(line.strip() for line in content.splitlines() if line.strip())
    parser = _TextExtractor()
    parser.feed(content)
    return "\n".join(parser.parts)


def _denied(field: str, message: str) -> StrategyError:
    return StrategyError(
        ErrorCategory.SOURCE_ACCESS_DENIED,
        "webpage source is prohibited by access policy",
        (ErrorIssue(field, "DENIED", message),),
    )
