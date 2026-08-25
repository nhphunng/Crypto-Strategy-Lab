from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from crypto_lab.domain.strategy.generation import GeneratedStrategyArtifact
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.security.source_content_protector import (
    ProtectedSourceContent,
    SourceContentProtector,
)


class EncryptedFilesystemArtifactStore:
    def __init__(self, root: Path, protector: SourceContentProtector) -> None:
        self._root = root
        self._protector = protector

    async def put(self, artifact: GeneratedStrategyArtifact) -> str:
        payload = json.dumps(
            {
                "id": str(artifact.id),
                "draftId": str(artifact.draft_id),
                "sourceCode": artifact.source_code,
                "contentFingerprint": artifact.content_fingerprint,
                "contractVersion": str(artifact.contract_version),
                "declaredImports": sorted(artifact.declared_imports),
                "capabilities": sorted(artifact.capabilities),
                "createdAt": artifact.created_at.isoformat(),
                "language": artifact.language,
                "languageVersion": artifact.language_version,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        protected = self._protector.protect(payload, source_id=artifact.content_fingerprint)
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self._root / f"{artifact.content_fingerprint}.artifact"
        if not path.exists():
            path.write_bytes(protected.key_id.encode() + b"\n" + protected.envelope)
            path.chmod(0o600)
        return artifact.content_fingerprint

    async def get(self, content_reference: str) -> GeneratedStrategyArtifact:
        if len(content_reference) != 64 or any(
            ch not in "0123456789abcdef" for ch in content_reference
        ):
            raise ValueError("invalid artifact reference")
        stored = (self._root / f"{content_reference}.artifact").read_bytes()
        key_id, envelope = stored.split(b"\n", 1)
        payload = json.loads(
            self._protector.reveal(
                ProtectedSourceContent(envelope, key_id.decode()), source_id=content_reference
            )
        )
        from datetime import datetime

        return GeneratedStrategyArtifact(
            id=UUID(payload["id"]),
            draft_id=UUID(payload["draftId"]),
            source_code=payload["sourceCode"],
            content_fingerprint=payload["contentFingerprint"],
            contract_version=SemanticVersion.parse(payload["contractVersion"]),
            declared_imports=frozenset(payload["declaredImports"]),
            capabilities=frozenset(payload["capabilities"]),
            created_at=datetime.fromisoformat(payload["createdAt"]),
            language=payload["language"],
            language_version=payload["languageVersion"],
        )
