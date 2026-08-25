from datetime import UTC, datetime, timedelta
from uuid import UUID

from crypto_lab.domain.strategy.generation import GenerationSourceType
from crypto_lab.domain.strategy.provenance import RetentionClass, StrategySourceSnapshot
from crypto_lab.infrastructure.security.source_content_protector import SourceContentProtector


class KeyProvider:
    key = b"r" * 32

    def generate_data_key(self):
        return self.key, b"wrapped", "retention-key"

    def unwrap_data_key(self, wrapped_key, key_id):
        return self.key


def test_raw_source_is_encrypted_with_at_most_thirty_day_expiry_and_minimal_provenance() -> None:
    captured = datetime(2026, 1, 1, tzinfo=UTC)
    protected = SourceContentProtector(KeyProvider()).protect(
        b"raw strategy source", source_id="snapshot"
    )
    snapshot = StrategySourceSnapshot(
        id=UUID(int=1),
        source_type=GenerationSourceType.NATURAL_LANGUAGE,
        content_fingerprint=StrategySourceSnapshot.fingerprint("raw strategy source"),
        encrypted_content=protected.envelope,
        encryption_key_id=protected.key_id,
        access_policy_version="source-access-v1",
        retention_class=RetentionClass.RAW_30_DAY_MAX,
        raw_content_expires_at=captured + timedelta(days=30),
    )
    assert b"raw strategy source" not in snapshot.encrypted_content
    assert snapshot.raw_content_expires_at == captured + timedelta(days=30)
    assert snapshot.content_fingerprint
