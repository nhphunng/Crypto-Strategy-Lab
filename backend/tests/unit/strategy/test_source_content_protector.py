from crypto_lab.infrastructure.security.source_content_protector import (
    ProtectedSourceContent,
    SourceContentProtector,
)


class FakeKeyProvider:
    key = b"k" * 32

    def generate_data_key(self):
        return self.key, b"wrapped-test-key", "test-key-v1"

    def unwrap_data_key(self, wrapped_key: bytes, key_id: str):
        assert wrapped_key == b"wrapped-test-key"
        assert key_id == "test-key-v1"
        return self.key


def test_source_content_uses_authenticated_envelope_encryption() -> None:
    protector = SourceContentProtector(FakeKeyProvider())
    protected = protector.protect(b"sensitive source", source_id="source-1")
    assert b"sensitive source" not in protected.envelope
    assert protector.reveal(protected, source_id="source-1") == b"sensitive source"

    tampered = ProtectedSourceContent(protected.envelope[:-1] + b"x", protected.key_id)
    try:
        protector.reveal(tampered, source_id="source-1")
    except ValueError:
        pass
    else:
        raise AssertionError("tampered envelope must fail")
