"""Password hashing and JWT access tokens.

The JWT signing secret is read from the JWT_SECRET_KEY environment variable and
validated when this module is imported. The API imports this module at startup,
so a missing or weak secret stops the app from starting instead of letting it
run with a secret an attacker could guess.

Generate a secret with:
    python -c "import secrets; print(secrets.token_urlsafe(64))"
"""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
import jwt  # PyJWT (python-jose has unfixed advisories, Phase F audit)

load_dotenv()

# Pinned on purpose. Letting the algorithm come from config (or from the token
# header) is how "alg confusion" attacks happen.
ALGORITHM = "HS256"

MIN_SECRET_BYTES = 32  # 256 bits, the HS256 key size
MIN_DISTINCT_CHARS = 16

# Values that have appeared in this repo, its docs, or common tutorials.
KNOWN_WEAK_SECRETS = {
    "shivansh",
    "secret",
    "changeme",
    "your_super_secret_jwt_key_here",
    "your-secret-key",
    "supersecret",
    "jwt_secret",
}
PLACEHOLDER_MARKERS = ("your_", "your-", "changeme", "change_me", "change-me", "placeholder", "example", "not-a-real")

GENERATE_HINT = 'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'

DEFAULT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days, the value used before this was configurable
MAX_EXPIRE_MINUTES = 60 * 24 * 30


class InsecureSecretError(RuntimeError):
    """Raised when JWT_SECRET_KEY is missing or too weak to use."""


def validate_jwt_secret(value: str | None) -> str:
    """Return the secret if it is safe to use, else raise InsecureSecretError.

    Error messages never include the secret itself.
    """
    if not value or not value.strip():
        raise InsecureSecretError(f"JWT_SECRET_KEY is not set. {GENERATE_HINT}")
    if len(value.encode("utf-8")) < MIN_SECRET_BYTES:
        raise InsecureSecretError(
            f"JWT_SECRET_KEY is shorter than {MIN_SECRET_BYTES} bytes. {GENERATE_HINT}"
        )
    lowered = value.lower()
    if lowered in KNOWN_WEAK_SECRETS or any(m in lowered for m in PLACEHOLDER_MARKERS):
        raise InsecureSecretError(
            f"JWT_SECRET_KEY is a known weak or placeholder value. {GENERATE_HINT}"
        )
    if len(set(value)) < MIN_DISTINCT_CHARS:
        raise InsecureSecretError(
            f"JWT_SECRET_KEY has too little variety to be random. {GENERATE_HINT}"
        )
    return value


def parse_expiry_minutes(raw: str | None) -> int:
    if raw is None or raw.strip() == "":
        return DEFAULT_EXPIRE_MINUTES
    try:
        minutes = int(raw)
    except ValueError:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be a whole number of minutes") from None
    if not 1 <= minutes <= MAX_EXPIRE_MINUTES:
        raise ValueError(f"ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and {MAX_EXPIRE_MINUTES}")
    return minutes


JWT_SECRET_KEY = validate_jwt_secret(os.getenv("JWT_SECRET_KEY"))
ACCESS_TOKEN_EXPIRE_MINUTES = parse_expiry_minutes(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# bcrypt only uses the first 72 bytes; bcrypt>=5 raises instead of truncating.
BCRYPT_MAX_BYTES = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """False (never an exception) for wrong, over-long or malformed input."""
    pw = plain_password.encode('utf-8')
    if len(pw) > BCRYPT_MAX_BYTES:
        pw = pw[:BCRYPT_MAX_BYTES]  # still do the work; no account accepts these (rule at signup)
        try:
            bcrypt.checkpw(pw, hashed_password.encode('utf-8'))
        except ValueError:
            pass
        return False
    try:
        return bcrypt.checkpw(pw, hashed_password.encode('utf-8'))
    except ValueError:
        return False


def create_access_token(user_id: str, session_id: str | None = None) -> str:
    """Signed token for one session. Since Phase F every valid token names a
    server-side session (`sid`), so it can be revoked before it expires."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def csrf_token_for(session_id: str) -> str:
    """CSRF token bound to one session (signed double-submit). The frontend
    reads it from a cookie and echoes it in a header; another site can't read
    our cookies, so it can't produce the header."""
    digest = hmac.new(JWT_SECRET_KEY.encode(), f"csrf:{session_id}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def csrf_matches(session_id: str, presented: str | None) -> bool:
    return bool(presented) and hmac.compare_digest(csrf_token_for(session_id), presented or "")


# A real bcrypt hash of a random value, checked when the email is unknown so a
# login takes the same time whether or not the account exists.
_DUMMY_HASH = bcrypt.hashpw(os.urandom(16), bcrypt.gensalt()).decode()


def verify_password_or_dummy(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        verify_password(plain_password, _DUMMY_HASH)
        return False
    return verify_password(plain_password, hashed_password)


def decode_access_token(token: str) -> dict:
    """Verify signature, algorithm, expiry and subject. Raises jwt.PyJWTError if invalid."""
    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
