"""Phase F security settings, all from the environment.

APP_ENV=production turns on: Secure + __Host- cookies, HSTS, and hides the
interactive API docs. Read these values at request time (not at import) so
tests can switch them.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _list(name: str, default: str) -> list[str]:
    return [v.strip().rstrip("/") for v in os.getenv(name, default).split(",") if v.strip()]


APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"

# Browser origins allowed to call the API. In production the browser talks to
# the frontend's own domain and Next.js proxies to the API, so this is the
# frontend origin (needed for the Origin check on writes, and CORS in dev).
CORS_ORIGINS = _list("CORS_ORIGINS", "http://localhost:3000")

# Session cookies.
SESSION_COOKIE = "grovii_session"
CSRF_COOKIE = "grovii_csrf"
CSRF_HEADER = "X-CSRF-Token"


def cookie_name(base: str) -> str:
    # __Host- cookies must be Secure, Path=/ and have no Domain: the browser
    # then refuses to let any other (sub)domain set or overwrite them.
    return f"__Host-{base}" if IS_PRODUCTION else base


def cookie_secure() -> bool:
    return IS_PRODUCTION or os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")


# Request bodies larger than this are refused with 413 before parsing.
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", str(64 * 1024)))

# Login lockout: this many failed logins for one email locks it for the window.
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCK_SECONDS = int(os.getenv("LOGIN_LOCK_SECONDS", "900"))

# The Next.js proxy sends the real client IP with this shared secret. Without
# a matching secret, X-Forwarded-For is ignored (anyone can set it).
PROXY_SHARED_SECRET = os.getenv("PROXY_SHARED_SECRET", "")
PROXY_SECRET_HEADER = "X-Grovii-Proxy-Secret"
CLIENT_IP_HEADER = "X-Grovii-Client-IP"

HSTS_VALUE = "max-age=63072000; includeSubDomains"
