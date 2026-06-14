"""Password hashing helpers.

Uses PBKDF2-HMAC-SHA256 from the standard library (salted and iterated) — no
extra dependency, and adequate for this trusted, self-hosted deployment.
Encoded format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.
"""

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Return an encoded PBKDF2 hash of the password (with a random salt)."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against an encoded hash, in constant time."""
    try:
        algorithm, iterations, salt_hex, hash_hex = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
    return hmac.compare_digest(digest, expected)
