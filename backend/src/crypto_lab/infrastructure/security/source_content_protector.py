from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class DataKeyProvider(Protocol):
    def generate_data_key(self) -> tuple[bytes, bytes, str]:
        """Return plaintext data key, wrapped data key, and opaque key identifier."""

    def unwrap_data_key(self, wrapped_key: bytes, key_id: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class ProtectedSourceContent:
    envelope: bytes
    key_id: str


class SourceContentProtector:
    """AES-256-GCM record encryption with externally wrapped per-record data keys."""

    def __init__(self, key_provider: DataKeyProvider) -> None:
        self._key_provider = key_provider

    def protect(self, content: bytes, *, source_id: str) -> ProtectedSourceContent:
        data_key, wrapped_key, key_id = self._key_provider.generate_data_key()
        if len(data_key) != 32:
            raise ValueError("key provider must supply a 256-bit data key")
        nonce = os.urandom(12)
        ciphertext = AESGCM(data_key).encrypt(nonce, content, source_id.encode())
        envelope = json.dumps(
            {
                "algorithm": "AES-256-GCM",
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "nonce": base64.b64encode(nonce).decode(),
                "version": 1,
                "wrappedKey": base64.b64encode(wrapped_key).decode(),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return ProtectedSourceContent(envelope, key_id)

    def reveal(self, protected: ProtectedSourceContent, *, source_id: str) -> bytes:
        try:
            envelope = json.loads(protected.envelope)
            if envelope["version"] != 1 or envelope["algorithm"] != "AES-256-GCM":
                raise ValueError("unsupported protected source envelope")
            wrapped_key = base64.b64decode(envelope["wrappedKey"], validate=True)
            nonce = base64.b64decode(envelope["nonce"], validate=True)
            ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("protected source envelope is malformed") from error
        data_key = self._key_provider.unwrap_data_key(wrapped_key, protected.key_id)
        return AESGCM(data_key).decrypt(nonce, ciphertext, source_id.encode())


class LocalAesKeyProvider:
    """Development key provider; production deployments should supply a managed-KMS adapter."""

    def __init__(self, master_key: bytes, key_id: str) -> None:
        if len(master_key) != 32:
            raise ValueError("master key must be 256 bits")
        self._master_key = master_key
        self._key_id = key_id

    def generate_data_key(self) -> tuple[bytes, bytes, str]:
        data_key = os.urandom(32)
        nonce = os.urandom(12)
        wrapped = nonce + AESGCM(self._master_key).encrypt(nonce, data_key, self._key_id.encode())
        return data_key, wrapped, self._key_id

    def unwrap_data_key(self, wrapped_key: bytes, key_id: str) -> bytes:
        if key_id != self._key_id or len(wrapped_key) < 13:
            raise ValueError("unknown or malformed wrapped data key")
        return AESGCM(self._master_key).decrypt(wrapped_key[:12], wrapped_key[12:], key_id.encode())
