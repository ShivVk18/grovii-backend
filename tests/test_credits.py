"""VULN-02: generation must be metered by credits, atomically, with refunds and a
per-user cap on active jobs."""
import threading
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.models.jobs import Job, JobStatus
from src.models.storyboard import Storyboard
from src.models.users import User
from tests.conftest import VALID_STORYBOARD


def _user_id_from(client, headers):
    return client.get("/auth/me", headers=headers).json()["id"]


def _set_credits(db, user_id, credits):
    db.query(User).filter(User.id == user_id).update({"credits": credits})
    db.commit()


def _credits(db, user_id):
    db.expire_all()
    return db.get(User, user_id).credits


def _generate(client, headers):
    return client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=headers)


# -------------------------------------------------------------- charging ----
def test_vuln02_zero_credits_is_refused_with_402_and_nothing_is_created(client, auth_headers, db, dispatched):
    uid = _user_id_from(client, auth_headers)
    _set_credits(db, uid, 0)

    r = _generate(client, auth_headers)

    assert r.status_code == 402, r.text
    body = r.json()
    assert body["code"] == "insufficient_credits"
    assert body["credits"] == 0
    assert isinstance(body["detail"], str)
    assert db.query(Storyboard).count() == 0
    assert db.query(Job).count() == 0
    assert not dispatched.called


def test_successful_dispatch_charges_one_credit_and_records_it_on_the_job(client, auth_headers, db, dispatched):
    uid = _user_id_from(client, auth_headers)
    _set_credits(db, uid, 3)

    r = _generate(client, auth_headers)

    assert r.status_code == 200, r.text
    assert _credits(db, uid) == 2
    job = db.get(Job, r.json()["job_id"])
    assert job.credits_charged == 1 and job.credits_refunded is False
    assert dispatched.called


def test_two_simultaneous_requests_with_one_credit_only_one_succeeds(db, user):
    """Ten threads, each with its own DB session, race for one credit."""
    from src.database import SessionLocal
    from src.Schemas.storyboard_schema import CreateStoryboardRequest
    from src.services.storyboard_service import reserve_generation

    uid = user.id  # read once: threads must not touch the fixture's session
    _set_credits(db, uid, 1)
    payload = CreateStoryboardRequest(**VALID_STORYBOARD)
    barrier = threading.Barrier(10)
    results: list[str] = []
    lock = threading.Lock()

    def attempt():
        session = SessionLocal()
        # Widen the race window: pause between reading the credit balance and
        # writing the deduction. Without the row lock every thread would read
        # "1 credit" during this pause and all of them would succeed.
        real_flush = session.flush

        def slow_flush(*args, **kwargs):
            time.sleep(0.2)
            return real_flush(*args, **kwargs)

        session.flush = slow_flush  # type: ignore[method-assign]
        try:
            barrier.wait()
            reserve_generation(session, payload, uid)
            outcome = "ok"
        except Exception as e:  # noqa: BLE001 - recording the outcome
            outcome = getattr(e, "code", type(e).__name__)
        finally:
            session.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == ["insufficient_credits"] * 9 + ["ok"], results
    assert _credits(db, uid) == 0
    assert db.query(Job).count() == 1


# ------------------------------------------------------- concurrency cap ----
def _active_job(db, user_id, minutes_ago=0, status=JobStatus.PENDING):
    sb = Storyboard(user_id=user_id, idea="x" * 10, goal="educate", tone="calm", style="pov",
                    audience="ab", duration=30, platform="reels", status="pending")
    db.add(sb)
    db.flush()
    job = Job(user_id=user_id, storyboard_id=sb.id, status=status)
    db.add(job)
    db.flush()
    job.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    db.commit()


def test_third_active_job_is_refused_with_429_and_no_charge(client, auth_headers, db):
    uid = _user_id_from(client, auth_headers)
    _set_credits(db, uid, 10)
    _active_job(db, uid, status=JobStatus.PENDING)
    _active_job(db, uid, status=JobStatus.PROCESSING)

    r = _generate(client, auth_headers)

    assert r.status_code == 429, r.text
    assert r.json()["code"] == "too_many_active_jobs"
    assert "Retry-After" in r.headers
    assert _credits(db, uid) == 10


def test_finished_and_stale_jobs_do_not_count_toward_the_cap(client, auth_headers, db):
    uid = _user_id_from(client, auth_headers)
    _set_credits(db, uid, 10)
    _active_job(db, uid, status=JobStatus.COMPLETED)
    _active_job(db, uid, status=JobStatus.FAILED)
    _active_job(db, uid, minutes_ago=120, status=JobStatus.PROCESSING)  # stuck: Phase C reaper's job
    _active_job(db, uid, status=JobStatus.PENDING)

    assert _generate(client, auth_headers).status_code == 200


# ---------------------------------------------------------------- refunds ----
def _charged_job(client, auth_headers, db):
    uid = _user_id_from(client, auth_headers)
    _set_credits(db, uid, 5)
    r = _generate(client, auth_headers)
    assert r.status_code == 200
    return uid, r.json()["storyboard_id"], r.json()["job_id"]


def _run_job_that_raises(sb_id, job_id, exc):
    from src.ai import graph as graph_module
    from src.services.jobs_services import generate_storyboard_job

    state = {**VALID_STORYBOARD, "hook": "", "scenes": [], "script": ""}
    with patch.object(graph_module.graph, "stream", side_effect=exc):
        with pytest.raises(type(exc)):
            generate_storyboard_job(state, sb_id, job_id)


def test_system_failure_refunds_the_credit(client, auth_headers, db):
    uid, sb_id, job_id = _charged_job(client, auth_headers, db)
    assert _credits(db, uid) == 4

    _run_job_that_raises(sb_id, job_id, RuntimeError("LLM provider down"))

    assert _credits(db, uid) == 5
    assert db.get(Job, job_id).credits_refunded is True


def test_refund_is_idempotent(client, auth_headers, db):
    from src.services.credits_service import refund_job_credits

    uid, _, job_id = _charged_job(client, auth_headers, db)
    assert refund_job_credits(db, job_id) is True
    assert refund_job_credits(db, job_id) is False
    assert refund_job_credits(db, job_id) is False
    assert _credits(db, uid) == 5


class ContentPolicyError(Exception):
    code = "content_policy_violation"


def test_user_fault_failure_is_not_refunded(client, auth_headers, db):
    uid, sb_id, job_id = _charged_job(client, auth_headers, db)

    _run_job_that_raises(sb_id, job_id, ContentPolicyError("rejected by safety system"))

    assert _credits(db, uid) == 4
    assert db.get(Job, job_id).credits_refunded is False
