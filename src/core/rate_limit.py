"""Rate limiting (slowapi) — per-account, to blunt scripted abuse of the LLM key.

Defense-in-depth behind the per-account feature flag: even a trusted (enabled)
account can't hammer the OpenAI-backed endpoints faster than a human would. The
key is the auth bearer token (one per session ≈ per account), falling back to
client IP for unauthenticated requests.
"""

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from src.settings import settings


def get_rate_limit_key(request: Request) -> str:
    """Rate-limit key: the bearer token (per account) if present, else client IP.

    A request carrying the secret bypass header gets a unique per-request key, so it
    never shares a bucket and is effectively unlimited (for your own bulk/admin runs).
    """
    bypass = settings.rate_limit_bypass_token
    if bypass and request.headers.get("X-Rate-Limit-Bypass") == bypass:
        return f"bypass:{id(request)}"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return f"user:{auth[7:]}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_rate_limit_key, enabled=settings.rate_limit_enabled)


def setup_rate_limiting(app: FastAPI) -> None:
    """Register the limiter + 429 handler on the app (call once in main)."""
    app.state.limiter = limiter
    # slowapi's handler signature is narrower than Starlette's expected type — known quirk.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
