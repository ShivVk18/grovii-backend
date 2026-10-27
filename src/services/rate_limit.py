"""Fixed-window rate limiting backed by Redis.

Each (rule, identity) pair gets a counter key that expires after the window.
The first request in a window creates the key with a TTL; later requests
increment it. When the count passes the limit, the request is refused with
HTTP 429 and a Retry-After header equal to the seconds left in the window.

If Redis is unreachable the limiter FAILS OPEN (allows the request and logs an
error). Reason: credits and the active-job cap (both in Postgres) still protect
the LLM budget, and a Redis outage should not lock every user out of login.
"""
import hashlib
import logging

from fastapi import Depends, Request

from src.api.errors import AppError
from src.config import limits
from src.config.dependencies_config import get_current_user
from src.services.redis_service import redis_client

logger = logging.getLogger("grovii.rate_limit")

PREFIX = "grovii:rl"


def _retry_after(ttl: int, window: int) -> int:
    # TTL is -1/-2 if the key has no expiry or vanished; fall back to the window.
    return ttl if ttl and ttl > 0 else max(1, window)


def client_ip(request: Request) -> str:
    # Only the direct peer address. X-Forwarded-For is NOT trusted here, because
    # anyone can set it. Behind a proxy, configure trusted proxies (Phase G).
    return request.client.host if request.client else "unknown"


def enforce(rule: str, identity: str, limit: tuple[int, int]) -> None:
    """Count one request for (rule, identity); raise AppError(429) if over the limit."""
    max_requests, window = limit
    # Hash the identity so emails and IPs are not stored in Redis in clear text.
    ident = hashlib.sha256(identity.lower().encode()).hexdigest()[:32]
    key = f"{PREFIX}:{rule}:{ident}"
    try:
        pipe = redis_client.pipeline()
        pipe.set(key, 0, ex=window, nx=True)
        pipe.incr(key)
        pipe.ttl(key)
        _, count, ttl = pipe.execute()
    except Exception as e:  # noqa: BLE001 - any Redis failure must not break the request
        logger.error("Rate limiter unavailable, allowing request (rule=%s): %s", rule, e)
        return
    if count > max_requests:
        retry = _retry_after(int(ttl), window)
        raise AppError(
            429, "rate_limited",
            f"Too many requests. Try again in {retry} seconds.",
            headers={"Retry-After": str(retry)},
            retry_after=retry,
        )


# ------------------------------------------------- FastAPI dependencies ----
# Limits are read from `limits` at request time, so they can be changed by env
# (and patched in tests) without re-importing.

def limit_login_ip(request: Request) -> None:
    enforce("login_ip", client_ip(request), limits.RATE_LOGIN_PER_IP)


def limit_register_ip(request: Request) -> None:
    enforce("register_ip", client_ip(request), limits.RATE_REGISTER_PER_IP)


def limit_generate(request: Request, current_user=Depends(get_current_user)) -> None:
    enforce("generate_ip", client_ip(request), limits.RATE_GENERATE_PER_IP)
    enforce("generate_user", str(current_user.id), limits.RATE_GENERATE_PER_USER)


def limit_create(current_user=Depends(get_current_user)) -> None:
    enforce("create_user", str(current_user.id), limits.RATE_CREATE_PER_USER)
