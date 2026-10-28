"""Phase F: security hardening.

Sessions are an httpOnly cookie plus a CSRF token (owner's choice). The browser
reaches the API through the frontend's own domain (Next.js proxy), so cookies
are first-party.
"""
import logging
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.models.caption import Caption
from src.models.jobs import Job
from src.models.scenes import Scene
from src.models.storyboard import Storyboard
from src.models.users import User
from tests.conftest import STRONG_PASSWORD, VALID_STORYBOARD

ORIGIN = "http://localhost:3000"


def _app():
    from src.main import app

    return app


def _register(c, email=None, password=STRONG_PASSWORD, **extra):
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    r = c.post("/auth/register", json={"username": email.split("@")[0], "email": email, "password": password, **extra})
    return email, r


def _session():
    """A browser-like client: registered, logged in, cookies stored."""
    c = TestClient(_app())
    email, r = _register(c)
    assert r.status_code == 200, r.text
    r = c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert r.status_code == 200, r.text
    return c, email


def _csrf(c):
    return {"X-CSRF-Token": c.cookies.get("grovii_csrf") or ""}


# ---------------------------------------------------------------- sessions ---

def test_login_sets_httponly_cookie_and_returns_no_token():
    c = TestClient(_app())
    email, _ = _register(c)
    r = c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert r.status_code == 200
    assert "access_token" not in r.json(), "token must not be readable by page scripts"
    cookies = r.headers.get_list("set-cookie")
    session = next(h for h in cookies if h.startswith("grovii_session="))
    assert "HttpOnly" in session and "SameSite=lax" in session and "Path=/" in session
    csrf = next(h for h in cookies if h.startswith("grovii_csrf="))
    assert "HttpOnly" not in csrf  # the frontend must read it to echo it back


def test_cookie_session_authenticates_reads():
    c, email = _session()
    r = c.get("/auth/me")
    assert r.status_code == 200 and r.json()["email"] == email


def test_writes_with_cookie_need_the_csrf_header():
    c, _ = _session()
    r = c.post("/storyboards", json=VALID_STORYBOARD)
    assert r.status_code == 403 and r.json()["code"] == "csrf_failed"
    r = c.post("/storyboards", json=VALID_STORYBOARD, headers={"X-CSRF-Token": "wrong"})
    assert r.status_code == 403
    r = c.post("/storyboards", json=VALID_STORYBOARD, headers=_csrf(c))
    assert r.status_code == 201, r.text


def test_writes_from_a_foreign_origin_are_refused():
    c, _ = _session()
    r = c.post("/storyboards", json=VALID_STORYBOARD, headers={**_csrf(c), "Origin": "https://evil.example"})
    assert r.status_code == 403


def test_logout_revokes_the_session_server_side():
    c, _ = _session()
    stolen = c.cookies.get("grovii_session")
    assert c.post("/auth/logout", headers=_csrf(c)).status_code == 200
    # Even a copy of the old cookie no longer works.
    other = TestClient(_app())
    other.cookies.set("grovii_session", stolen)
    assert other.get("/auth/me").status_code == 401


def test_logout_all_revokes_every_session_of_the_user():
    c1, email = _session()
    c2 = TestClient(_app())
    assert c2.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD}).status_code == 200
    assert c1.post("/auth/logout-all", headers=_csrf(c1)).status_code == 200
    assert c2.get("/auth/me").status_code == 401


def test_tokens_without_a_session_id_are_rejected():
    from src.config.security_config import create_access_token

    c, _ = _session()
    uid = c.get("/auth/me").json()["id"]
    legacy = create_access_token(uid)  # pre-Phase-F style: no session id
    r = TestClient(_app()).get("/auth/me", headers={"Authorization": f"Bearer {legacy}"})
    assert r.status_code == 401


# ------------------------------------------------------- CORS and headers ---

def test_cors_allows_only_configured_origins():
    c = TestClient(_app())
    pre = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-csrf-token"}
    ok = c.options("/storyboards", headers={"Origin": ORIGIN, **pre})
    assert ok.headers.get("access-control-allow-origin") == ORIGIN
    bad = c.options("/storyboards", headers={"Origin": "https://evil.example", **pre})
    assert bad.headers.get("access-control-allow-origin") is None
    assert ok.headers.get("access-control-allow-methods") != "*"


def test_security_headers_on_every_response():
    c = TestClient(_app())
    for r in (c.get("/"), c.get("/storyboards"), c.post("/auth/login", json={})):
        h = r.headers
        assert h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["referrer-policy"] == "no-referrer"


def test_hsts_secure_cookies_and_no_docs_in_production(monkeypatch):
    from src.config import security_settings as s

    monkeypatch.setattr(s, "IS_PRODUCTION", True)
    c = TestClient(_app())
    assert "max-age=" in c.get("/").headers.get("strict-transport-security", "")
    email, _ = _register(c)
    r = c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    session = next(h for h in r.headers.get_list("set-cookie") if "grovii_session=" in h)
    assert session.startswith("__Host-grovii_session=") and "Secure" in session
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


# --------------------------------------------------------------- passwords ---

@pytest.mark.parametrize("password,why", [
    ("short1!", "too short"),
    ("password1234", "common"),
    ("aaaaaaaaaaaa", "too simple"),
    ("x" * 73, "over bcrypt's 72-byte limit"),
])
def test_weak_passwords_are_rejected(password, why):
    _, r = _register(TestClient(_app()), password=password)
    assert r.status_code == 422, why
    assert "password" in r.json()["errors"], why


def test_password_cannot_contain_the_email_name():
    email = f"marisol{uuid.uuid4().hex[:4]}@example.com"
    _, r = _register(TestClient(_app()), email=email, password=email.split("@")[0] + "-2026!")
    assert r.status_code == 422 and "password" in r.json()["errors"]


# ------------------------------------------------------------------ login ----

def test_login_errors_are_generic():
    c = TestClient(_app())
    email, _ = _register(c)
    wrong_pw = c.post("/auth/login", json={"email": email, "password": "Wrong-password-123"})
    no_user = c.post("/auth/login", json={"email": f"nobody{uuid.uuid4().hex[:6]}@example.com", "password": "Wrong-password-123"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_unknown_email_still_runs_a_password_check():
    """Same work for unknown emails, so response time doesn't reveal accounts."""
    import bcrypt

    calls = []
    real = bcrypt.checkpw
    with patch("bcrypt.checkpw", side_effect=lambda *a: calls.append(1) or real(*a)):
        TestClient(_app()).post("/auth/login", json={"email": f"x{uuid.uuid4().hex[:6]}@example.com", "password": "Whatever-123"})
    assert calls, "no password hash was checked for an unknown email"


def test_repeated_failures_lock_the_account_temporarily():
    c = TestClient(_app())
    email, _ = _register(c)
    for _ in range(5):
        assert c.post("/auth/login", json={"email": email, "password": "Wrong-password-123"}).status_code == 401
    r = c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_successful_login_resets_the_failure_count():
    c = TestClient(_app())
    email, _ = _register(c)
    for _ in range(4):
        c.post("/auth/login", json={"email": email, "password": "Wrong-password-123"})
    assert c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD}).status_code == 200
    for _ in range(4):
        c.post("/auth/login", json={"email": email, "password": "Wrong-password-123"})
    assert c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD}).status_code == 200


def test_duplicate_registration_does_not_leak_database_errors():
    c = TestClient(_app())
    email, r1 = _register(c)
    assert r1.status_code == 200
    _, dup_email = _register(c, email=email)
    _, dup_name = _register(c, email=f"{email.split('@')[0]}@other.example")  # same username
    for r in (dup_email, dup_name):
        assert r.status_code == 409, r.text
        body = r.text.lower()
        for leak in ("integrity", "psycopg", "sql", "constraint", "duplicate key", "traceback"):
            assert leak not in body, r.text


# ------------------------------------------------------- errors and logs ----

def test_unhandled_errors_return_a_generic_500():
    app = _app()

    @app.get("/__boom")
    def _boom():
        raise RuntimeError("psycopg2 password=hunter2 at /srv/app/secret.py line 3")

    try:
        r = TestClient(app, raise_server_exceptions=False).get("/__boom")
    finally:
        app.router.routes = [rt for rt in app.router.routes if getattr(rt, "path", "") != "/__boom"]
    assert r.status_code == 500
    assert r.json()["code"] == "internal_error"
    assert "hunter2" not in r.text and "psycopg2" not in r.text and "Traceback" not in r.text


def test_logs_never_contain_passwords_or_session_tokens(caplog):
    caplog.set_level(logging.DEBUG)
    c, email = _session()
    token = c.cookies.get("grovii_session")
    c.post("/auth/login", json={"email": email, "password": "Wrong-password-xyz"})
    c.get("/auth/me")
    text = caplog.text
    assert STRONG_PASSWORD not in text and "Wrong-password-xyz" not in text
    assert token not in text


def test_failed_ai_steps_do_not_log_generated_or_creator_text(caplog):
    """A parser error carries the whole model reply; logs must not copy it."""
    from langchain_core.exceptions import OutputParserException

    from src.ai.nodes import music_node

    marker = "CREATOR-PRIVATE-PHONE-555-0199"
    caplog.set_level(logging.DEBUG)
    err = OutputParserException(f"Invalid json output: {marker} ... " * 20)
    with patch.object(music_node.openai_service, "get_llm", side_effect=err):
        out = music_node.music_node({"idea": marker, "script": marker, "hook": marker})
    assert out.get("scene_music") == []  # the step failed as intended
    assert marker not in caplog.text


# --------------------------------------------- account deletion and export ---

def test_export_contains_my_data_and_no_secrets(db):
    c, email = _session()
    r = c.post("/storyboards", json=VALID_STORYBOARD, headers=_csrf(c))
    assert r.status_code == 201
    r = c.get("/auth/me/export")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    data = r.json()
    assert data["account"]["email"] == email
    assert data["storyboards"][0]["idea"] == VALID_STORYBOARD["idea"]
    assert "hashed_password" not in r.text and "grovii_session" not in r.text


def test_delete_account_needs_password_and_csrf(db):
    c, _ = _session()
    assert c.request("DELETE", "/auth/me", json={"password": STRONG_PASSWORD}).status_code == 403  # no CSRF
    r = c.request("DELETE", "/auth/me", json={"password": "Wrong-password-123"}, headers=_csrf(c))
    assert r.status_code == 403 and r.json()["code"] == "wrong_password"


def test_delete_account_removes_all_my_data(db):
    c, email = _session()
    uid = c.get("/auth/me").json()["id"]
    sb = Storyboard(user_id=uid, idea="x" * 20, goal="educate", tone="calm", style="talking_head",
                    audience="x", duration=30, platform="reels", status="completed")
    db.add(sb)
    db.flush()
    db.add_all([Scene(storyboard_id=sb.id, scene_number=1), Caption(storyboard_id=sb.id, caption="hi"),
                Job(user_id=uid, storyboard_id=sb.id, status="completed", progress=100)])
    db.commit()
    sb_id = sb.id

    r = c.request("DELETE", "/auth/me", json={"password": STRONG_PASSWORD}, headers=_csrf(c))
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.query(User).filter(User.email == email).count() == 0
    assert db.query(Storyboard).filter(Storyboard.user_id == uid).count() == 0
    assert db.query(Scene).filter(Scene.storyboard_id == sb_id).count() == 0
    assert db.query(Caption).filter(Caption.storyboard_id == sb_id).count() == 0
    assert db.query(Job).filter(Job.user_id == uid).count() == 0
    # The session is gone too.
    assert c.get("/auth/me").status_code == 401


def test_deleting_a_storyboard_deletes_its_content(db):
    c, _ = _session()
    uid = c.get("/auth/me").json()["id"]
    sb = Storyboard(user_id=uid, idea="y" * 20, goal="educate", tone="calm", style="talking_head",
                    audience="x", duration=30, platform="reels", status="completed")
    db.add(sb)
    db.flush()
    db.add_all([Scene(storyboard_id=sb.id, scene_number=1, title="private scene"),
                Caption(storyboard_id=sb.id, caption="private caption")])
    db.commit()
    assert c.delete(f"/storyboards/{sb.id}", headers=_csrf(c)).status_code == 200
    db.expire_all()
    assert db.query(Scene).filter(Scene.title == "private scene").count() == 0, "orphaned scene left behind"
    assert db.query(Caption).filter(Caption.caption == "private caption").count() == 0


# ------------------------------------------- input abuse (re-test, rule 8) ---

def test_oversized_bodies_are_refused_before_parsing():
    c, _ = _session()
    big = {**VALID_STORYBOARD, "idea": "a" * 2_000_000}
    r = c.post("/storyboards", json=big, headers=_csrf(c))
    assert r.status_code == 413 and r.json()["code"] == "body_too_large"


def test_oversized_chunked_bodies_are_refused():
    c, _ = _session()

    def gen():
        for _ in range(200):
            yield b"x" * 10_000

    r = c.post("/storyboards", content=gen(), headers={**_csrf(c), "Content-Type": "application/json"})
    assert r.status_code == 413


def test_mass_assignment_fields_are_rejected(db):
    c = TestClient(_app())
    _, r = _register(c, credits=999999, plan="pro", is_verified=True)
    assert r.status_code == 422 and {"credits", "plan", "is_verified"} & set(r.json()["errors"])
    c, _ = _session()
    r = c.post("/storyboards", json=VALID_STORYBOARD, headers=_csrf(c))
    sb_id = r.json()["id"]
    for field, value in (("user_id", "someone-else"), ("status", "completed"), ("hook", "x"), ("credits", 5)):
        r = c.patch(f"/storyboards/{sb_id}", json={field: value}, headers=_csrf(c))
        assert r.status_code == 422, (field, r.text)


@pytest.mark.parametrize("payload", [
    "'; DROP TABLE users; --",
    "\" OR 1=1 --",
    "Robert'); DELETE FROM storyboards WHERE ('1'='1",
])
def test_sql_injection_strings_are_stored_as_text(payload, db):
    c, _ = _session()
    r = c.post("/storyboards", json={**VALID_STORYBOARD, "idea": f"Video idea {payload}"}, headers=_csrf(c))
    assert r.status_code == 201, r.text
    assert c.get(f"/storyboards/{r.json()['id']}").json()["idea"] == f"Video idea {payload}"
    r = TestClient(_app()).post("/auth/login", json={"email": "a@example.com", "password": payload})
    assert r.status_code in (401, 429)
    assert db.query(User).count() > 0


def test_stored_xss_is_returned_as_json_text_with_nosniff():
    c, _ = _session()
    xss = "<script>alert(1)</script> idea text"
    r = c.post("/storyboards", json={**VALID_STORYBOARD, "idea": xss}, headers=_csrf(c))
    r = c.get(f"/storyboards/{r.json()['id']}")
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.json()["idea"] == xss  # stored as given; the frontend renders it as text (Phase E test)


# -------------------------------------------------- client IP behind proxy ---

def _ip_for(headers, monkeypatch, secret="proxy-secret-for-tests-0123456789"):
    from starlette.requests import Request

    from src.config import security_settings as s
    from src.services.rate_limit import client_ip

    monkeypatch.setattr(s, "PROXY_SHARED_SECRET", secret)
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return client_ip(Request({"type": "http", "headers": raw, "client": ("10.0.0.5", 1234)}))


def test_forwarded_client_ip_is_used_only_with_the_proxy_secret(monkeypatch):
    good = {"X-Grovii-Proxy-Secret": "proxy-secret-for-tests-0123456789", "X-Grovii-Client-IP": "203.0.113.7"}
    assert _ip_for(good, monkeypatch) == "203.0.113.7"
    forged = {"X-Grovii-Proxy-Secret": "guess", "X-Grovii-Client-IP": "203.0.113.7", "X-Forwarded-For": "1.2.3.4"}
    assert _ip_for(forged, monkeypatch) == "10.0.0.5"
    assert _ip_for(good, monkeypatch, secret="") == "10.0.0.5"  # no secret configured: never trust headers


# ------------------------------------------ settings actions are real (F) ---

def test_change_password_needs_current_password_and_rules():
    c, email = _session()
    r = c.post("/auth/change-password", json={"current_password": "Wrong-password-123", "new_password": "new-strong-pass-2026"},
               headers=_csrf(c))
    assert r.status_code == 403 and r.json()["code"] == "wrong_password"
    r = c.post("/auth/change-password", json={"current_password": STRONG_PASSWORD, "new_password": "short"}, headers=_csrf(c))
    assert r.status_code == 422 and "new_password" in r.json()["errors"]


def test_change_password_works_and_signs_out_other_devices():
    c1, email = _session()
    c2 = TestClient(_app())
    assert c2.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD}).status_code == 200
    r = c1.post("/auth/change-password", json={"current_password": STRONG_PASSWORD, "new_password": "new-strong-pass-2026"},
                headers=_csrf(c1))
    assert r.status_code == 200, r.text
    assert c1.get("/auth/me").status_code == 200       # this device stays signed in
    assert c2.get("/auth/me").status_code == 401       # other devices are signed out
    fresh = TestClient(_app())
    assert fresh.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD}).status_code == 401
    assert fresh.post("/auth/login", json={"email": email, "password": "new-strong-pass-2026"}).status_code == 200


def test_update_username():
    c, _ = _session()
    new = f"creator_{uuid.uuid4().hex[:6]}"
    r = c.patch("/auth/me", json={"username": new}, headers=_csrf(c))
    assert r.status_code == 200 and r.json()["username"] == new
    assert c.get("/auth/me").json()["username"] == new
    assert c.patch("/auth/me", json={"username": "x"}, headers=_csrf(c)).status_code == 422
    assert c.patch("/auth/me", json={"credits": 1_000_000}, headers=_csrf(c)).status_code == 422
    other, _ = _session()
    taken = other.patch("/auth/me", json={"username": new}, headers=_csrf(other))
    assert taken.status_code == 409
