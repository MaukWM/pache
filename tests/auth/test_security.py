"""Tests for password hashing helpers."""

from src.auth.security import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    """A password verifies against its own hash."""
    encoded = hash_password("secret123")
    assert verify_password("secret123", encoded)


def test_verify_rejects_wrong_password() -> None:
    """A different password does not verify."""
    encoded = hash_password("secret123")
    assert not verify_password("wrong-password", encoded)


def test_hash_is_salted_and_unique() -> None:
    """Hashing the same password twice yields different encodings (random salt)."""
    assert hash_password("same") != hash_password("same")


def test_verify_handles_malformed_hash() -> None:
    """Malformed or empty encodings fail closed instead of raising."""
    assert not verify_password("secret", "not-a-valid-hash")
    assert not verify_password("secret", "")
    assert not verify_password("secret", "bogus$1$2$3")
