"""VULN-01: JWT secret must come from the environment, be strong, and tokens
must be verified for signature, algorithm, expiry and subject."""
import os
import secrets
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import jwt

BACKEND_ROOT = Path(__file__).resolve().parents[1]
OLD_HARDCODED_SECRET = "shivansh"  # the leaked value from the eval report
TEST_PASSWORD = "pw-123456789"  # gitleaks:allow  (test-only password, not a secret)


# ------------------------------------------------------ secret validation ----
WEAK_SECRETS = {
    "empty": "",
    "old hardcoded value": OLD_HARDCODED_SECRET,
    "short random": secrets.token_hex(8),            # 16 chars
    "31 bytes": "k" * 20 + "Zq9!xY7#mN2",            # 31 chars
    "example placeholder": "your_super_secret_jwt_key_here",
    "long placeholder": "please-change-me-this-is-not-a-real-secret-123",
    "low variety": "a" * 64,
    "repeated short pattern": "abc123" * 8,
}


@pytest.mark.parametrize("value", WEAK_SECRETS.values(), ids=WEAK_SECRETS.keys())
def test_weak_or_missing_secret_is_rejected(value):
    from src.config.security_config import InsecureSecretError, validate_jwt_secret

    with pytest.raises(InsecureSecretError) as exc:
        validate_jwt_secret(value)
    # The error must explain the fix but never echo the secret back.
    if value:
        assert value not in str(exc.value)
    assert "JWT_SECRET_KEY" in str(exc.value)


def test_none_secret_is_rejected():
    from src.config.security_config import InsecureSecretError, validate_jwt_secret

    with pytest.raises(InsecureSecretError):
        validate_jwt_secret(None)


def test_strong_secret_is_accepted():
    from src.config.security_config import validate_jwt_secret

    strong = secrets.token_urlsafe(64)
    assert validate_jwt_secret(strong) == strong


# ------------------------------------------------------ app refuses start ----
def _import_app(jwt_value: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "JWT_SECRET_KEY": jwt_value}
    return subprocess.run(
        [sys.executable, "-c", "import src.main"],
        cwd=BACKEND_ROOT, env=env, capture_output=True, text=True, timeout=120,
    )


@pytest.mark.parametrize("value", ["", OLD_HARDCODED_SECRET, "your_super_secret_jwt_key_here"],
                         ids=["missing", "old-hardcoded", "placeholder"])
def test_app_refuses_to_start_with_bad_secret(value):
    result = _import_app(value)
    assert result.returncode != 0, "app started with an insecure JWT secret"
    error_line = result.stderr.strip().splitlines()[-1]
    assert "InsecureSecretError" in error_line and "JWT_SECRET_KEY" in error_line
    if value:
        # Check only the error message: the traceback contains file paths,
        # which may legitimately include the same text (e.g. a username).
        assert value not in error_line


def test_app_starts_with_strong_secret():
    result = _import_app(secrets.token_urlsafe(64))
    assert result.returncode == 0, result.stderr[-2000:]


# ------------------------------------------------------ token verification ----
@pytest.fixture
def user_id(client):
    r = client.post("/auth/register", json={"username": "jwtuser", "email": "jwt@example.com", "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["user_id"]


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})


def _session_id(user_id):
    """A live server-side session (Phase F tokens must name one)."""
    from src.database import SessionLocal
    from src.models.sessions import UserSession

    with SessionLocal() as s:
        row = UserSession(user_id=user_id, expires_at=datetime.utcnow() + timedelta(hours=1))
        s.add(row)
        s.commit()
        return row.id


def _claims(user_id, **overrides):
    now = datetime.now(timezone.utc)
    claims = {"sub": user_id, "sid": _session_id(user_id), "iat": now, "exp": now + timedelta(minutes=5)}
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


def test_valid_token_is_accepted(client, user_id):
    token = jwt.encode(_claims(user_id), os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    assert _me(client, token).status_code == 200


def test_token_forged_with_old_hardcoded_secret_is_rejected(client, user_id):
    forged = jwt.encode(_claims(user_id), OLD_HARDCODED_SECRET, algorithm="HS256")
    assert _me(client, forged).status_code == 401


def test_expired_token_is_rejected(client, user_id):
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    token = jwt.encode(_claims(user_id, iat=past, exp=past + timedelta(minutes=1)),
                       os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    assert _me(client, token).status_code == 401


def test_token_without_exp_is_rejected(client, user_id):
    token = jwt.encode(_claims(user_id, exp=None), os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    assert _me(client, token).status_code == 401


def test_token_with_other_algorithm_is_rejected(client, user_id):
    token = jwt.encode(_claims(user_id), os.environ["JWT_SECRET_KEY"], algorithm="HS512")
    assert _me(client, token).status_code == 401


def test_unsigned_alg_none_token_is_rejected(client, user_id):
    import base64
    import json

    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    exp = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
    token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': user_id, 'exp': exp})}."
    assert _me(client, token).status_code == 401


def test_issued_token_has_exp_and_iat_matching_config(client, user_id):
    from src.config.security_config import ACCESS_TOKEN_EXPIRE_MINUTES

    r = client.post("/auth/login", json={"email": "jwt@example.com", "password": TEST_PASSWORD})
    claims = jwt.decode(r.cookies["grovii_session"], options={"verify_signature": False})
    assert claims.get("sid"), "token must name a server-side session"
    assert claims["sub"] == user_id
    assert "iat" in claims and "exp" in claims
    assert abs((claims["exp"] - claims["iat"]) - ACCESS_TOKEN_EXPIRE_MINUTES * 60) <= 1


@pytest.mark.parametrize("raw", ["abc", "0", "-5", "100000"])
def test_bad_expiry_setting_is_rejected(raw):
    from src.config.security_config import parse_expiry_minutes

    with pytest.raises(ValueError):
        parse_expiry_minutes(raw)


def test_expiry_setting_default_and_custom():
    from src.config.security_config import parse_expiry_minutes

    assert parse_expiry_minutes(None) == 60 * 24 * 7  # unchanged from before: 7 days
    assert parse_expiry_minutes("30") == 30
