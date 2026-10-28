"""Phase F: cross-tenant access (IDOR) matrix for EVERY route.

The route list is read from the app itself, so a new route that is not
classified here fails `test_every_route_is_classified` until someone decides
whether it is public, and which tests cover it.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from src.models.jobs import Job, JobStatus
from src.models.scenes import Scene
from src.models.storyboard import Storyboard
from tests.conftest import STRONG_PASSWORD

PUBLIC = {
    ("GET", "/"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/health"),
    # FastAPI docs (disabled in production by Phase F config, see test_security_hardening)
    ("GET", "/openapi.json"), ("GET", "/docs"), ("GET", "/docs/oauth2-redirect"), ("GET", "/redoc"),
}

# Routes that act on one storyboard/job owned by someone.
OWNED = {
    ("GET", "/storyboards/{storyboard_id}"),
    ("PATCH", "/storyboards/{storyboard_id}"),
    ("DELETE", "/storyboards/{storyboard_id}"),
    ("GET", "/storyboards/jobs/{job_id}"),
    ("POST", "/storyboards/jobs/{job_id}/cancel"),
}

# Routes that act on "my" data only; checked to never show another user's data.
SELF = {
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("GET", "/auth/me/export"),
    ("DELETE", "/auth/me"),
    ("POST", "/auth/logout-all"),
    ("POST", "/auth/change-password"),
    ("PATCH", "/auth/me"),
    ("GET", "/storyboards"),
    ("POST", "/storyboards"),
    ("POST", "/storyboards/generate"),
    ("GET", "/storyboards/jobs"),
}


def _routes():
    from src.main import app

    out = set()
    for r in app.routes:
        for m in getattr(r, "methods", None) or ():
            if m in ("HEAD", "OPTIONS"):
                continue
            out.add((m, r.path))
    return out


def test_every_route_is_classified():
    unknown = _routes() - PUBLIC - OWNED - SELF
    assert not unknown, f"Classify these routes in test_idor_matrix.py: {sorted(unknown)}"


@pytest.mark.parametrize("method,path", sorted(OWNED | SELF))
def test_protected_routes_reject_anonymous_requests(method, path):
    from src.main import app

    if (method, path) not in _routes():
        pytest.skip("route not present")
    c = TestClient(app)
    url = path.replace("{storyboard_id}", str(uuid.uuid4())).replace("{job_id}", str(uuid.uuid4()))
    r = c.request(method, url, json={})
    assert r.status_code == 401, (method, path, r.status_code, r.text)


def _login(email: str):
    from src.main import app

    c = TestClient(app)
    r = c.post("/auth/register", json={"username": email.split("@")[0], "email": email, "password": STRONG_PASSWORD})
    assert r.status_code == 200, r.text
    r = c.post("/auth/login", json={"email": email, "password": STRONG_PASSWORD})
    assert r.status_code == 200, r.text
    # Cookie session; send the CSRF header on writes like the frontend does.
    c.headers["X-CSRF-Token"] = c.cookies.get("grovii_csrf") or ""
    return c


@pytest.fixture
def two_users(db):
    alice = _login(f"alice_{uuid.uuid4().hex[:6]}@example.com")
    bob = _login(f"bob_{uuid.uuid4().hex[:6]}@example.com")
    alice_id = alice.get("/auth/me").json()["id"]
    secret = f"ALICE-PRIVATE-{uuid.uuid4().hex[:6]}"
    sb = Storyboard(user_id=alice_id, title=secret, idea=secret, goal="educate", tone="calm", style="talking_head",
                    audience="x", duration=30, platform="reels", status="completed", hook=secret, script=secret)
    db.add(sb)
    db.flush()
    db.add(Scene(storyboard_id=sb.id, scene_number=1, title=secret, what_to_show=secret))
    job = Job(user_id=alice_id, storyboard_id=sb.id, status=JobStatus.QUEUED, progress=0)
    db.add(job)
    db.commit()
    return alice, bob, sb.id, job.id, secret


@pytest.mark.parametrize("method,path", sorted(OWNED))
def test_other_users_cannot_touch_owned_resources(two_users, method, path, db):
    alice, bob, sb_id, job_id, secret = two_users
    url = path.replace("{storyboard_id}", sb_id).replace("{job_id}", job_id)
    body = {"title": "hacked"} if method == "PATCH" else None
    r = bob.request(method, url, json=body)
    assert r.status_code in (403, 404), (method, path, r.status_code, r.text)
    assert secret not in r.text
    # Nothing changed for the owner.
    db.expire_all()
    sb = db.get(Storyboard, sb_id)
    assert sb is not None and sb.title == secret
    assert db.get(Job, job_id).status == JobStatus.QUEUED
    # Sanity: the owner can read it.
    assert alice.get(f"/storyboards/{sb_id}").status_code == 200


def test_lists_and_export_never_include_other_users_data(two_users):
    _, bob, sb_id, job_id, secret = two_users
    for url in ("/storyboards", "/storyboards/jobs", "/auth/me", "/auth/me/export"):
        r = bob.get(url)
        assert r.status_code == 200, (url, r.text)
        assert secret not in r.text and sb_id not in r.text and job_id not in r.text, url


def test_deleting_my_account_does_not_touch_other_users(two_users, db):
    alice, bob, sb_id, _, secret = two_users
    r = bob.request("DELETE", "/auth/me", json={"password": STRONG_PASSWORD})
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.get(Storyboard, sb_id) is not None
    assert alice.get(f"/storyboards/{sb_id}").status_code == 200
