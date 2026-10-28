"""Phase B: Redis-backed rate limits on login, signup and generation."""
import time
import uuid
from unittest.mock import patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from src.config import limits
from src.models.users import User
from src.config import security_settings
from tests.conftest import VALID_STORYBOARD, login_token

TEST_PASSWORD = "pw-123456789"  # gitleaks:allow  (test-only password, not a secret)


def _login(client, email, password="wrong-password"):
    return client.post("/auth/login", json={"email": email, "password": password})


def _register(client):
    e = f"{uuid.uuid4().hex[:8]}@example.com"
    return client.post("/auth/register", json={"username": e.split("@")[0], "email": e, "password": TEST_PASSWORD})


def assert_rate_limited(r):
    assert r.status_code == 429, r.text
    body = r.json()
    assert body["code"] == "rate_limited"
    assert isinstance(body["detail"], str) and "Try again" in body["detail"]
    assert int(r.headers["Retry-After"]) >= 1
    assert body["retry_after"] == int(r.headers["Retry-After"])


# ------------------------------------------------------------------ login ----
def test_login_is_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(limits, "RATE_LOGIN_PER_IP", (3, 60))
    for i in range(3):
        assert _login(client, f"user{i}@example.com").status_code == 401
    assert_rate_limited(_login(client, "another@example.com"))


def test_login_is_limited_per_email_across_ips(client, monkeypatch):
    # Since Phase F: failed attempts per account lock it for a while (any IP).
    monkeypatch.setattr(limits, "RATE_LOGIN_PER_IP", (100, 60))
    monkeypatch.setattr(security_settings, "LOGIN_MAX_FAILURES", 2)
    assert _login(client, "victim@example.com").status_code == 401
    assert _login(client, "VICTIM@example.com").status_code == 401  # same account, different case
    r = _login(client, "victim@example.com")
    assert r.status_code == 429 and r.json()["code"] == "login_locked" and int(r.headers["Retry-After"]) >= 1
    assert _login(client, "someone-else@example.com").status_code == 401


def test_default_login_limit_is_enforced(client):
    """No monkeypatching: the shipped default (10/min per IP) applies."""
    per_ip, _ = limits.RATE_LOGIN_PER_IP
    for i in range(per_ip):
        assert _login(client, f"u{i}@example.com").status_code == 401
    assert_rate_limited(_login(client, "x@example.com"))


def test_limit_resets_after_the_window(client, monkeypatch):
    monkeypatch.setattr(limits, "RATE_LOGIN_PER_IP", (1, 1))
    assert _login(client, "a@example.com").status_code == 401
    assert_rate_limited(_login(client, "a@example.com"))
    time.sleep(1.2)
    assert _login(client, "a@example.com").status_code == 401


# ----------------------------------------------------------------- signup ----
def test_signup_is_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(limits, "RATE_REGISTER_PER_IP", (2, 3600))
    assert _register(client).status_code == 200
    assert _register(client).status_code == 200
    assert_rate_limited(_register(client))


# ------------------------------------------------------------- generation ----
def test_generation_is_limited_per_user_and_refusal_is_not_charged(client, auth_headers, db, monkeypatch):
    monkeypatch.setattr(limits, "RATE_GENERATE_PER_USER", (3, 3600))
    monkeypatch.setattr(limits, "MAX_ACTIVE_JOBS_PER_USER", 100)
    uid = client.get("/auth/me", headers=auth_headers).json()["id"]
    db.query(User).filter(User.id == uid).update({"credits": 50})
    db.commit()

    for _ in range(3):
        assert client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers).status_code == 200
    assert_rate_limited(client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers))

    db.expire_all()
    assert db.get(User, uid).credits == 47  # the refused request cost nothing


def test_generation_is_limited_per_ip_across_users(client, db, monkeypatch):
    monkeypatch.setattr(limits, "RATE_GENERATE_PER_IP", (2, 3600))
    monkeypatch.setattr(limits, "RATE_GENERATE_PER_USER", (100, 3600))
    monkeypatch.setattr(limits, "RATE_REGISTER_PER_IP", (100, 3600))

    def headers_for_new_user():
        e = f"{uuid.uuid4().hex[:8]}@example.com"
        client.post("/auth/register", json={"username": e.split("@")[0], "email": e, "password": TEST_PASSWORD})
        token = login_token(client, e, TEST_PASSWORD)
        return {"Authorization": f"Bearer {token}"}

    assert client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=headers_for_new_user()).status_code == 200
    assert client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=headers_for_new_user()).status_code == 200
    assert_rate_limited(client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=headers_for_new_user()))


# ---------------------------------------------------------- Redis failure ----
def test_redis_outage_fails_open_instead_of_breaking_login(client):
    from src.services.redis_service import redis_client

    with patch.object(redis_client, "pipeline", side_effect=RedisConnectionError("down")):
        r = _login(client, "nobody@example.com")
    assert r.status_code == 401  # normal answer, not a 500 and not a 429


@pytest.mark.parametrize("bad", ["0", "-1"])
def test_retry_after_is_never_below_one(bad):
    from src.services.rate_limit import _retry_after

    assert _retry_after(int(bad), 60) >= 1
