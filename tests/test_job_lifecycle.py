"""Phase C: queue dispatch, job/storyboard status lifecycle, fail-closed saving,
retries with idempotency, stuck-job reaper and cancellation."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.models.jobs import Job, JobStatus
from src.models.scenes import Scene
from src.models.storyboard import Storyboard
from src.models.users import User
from src.Schemas.storyboard_schema import CreateStoryboardRequest
from tests.conftest import STRONG_PASSWORD, VALID_STORYBOARD, login_token

GOOD_SCENES = [{"title": f"S{i}", "duration": 6, "what_to_show": "Pour coffee",
                "voiceover_example": f"Line {i}"} for i in range(1, 6)]
GOOD_UPDATES = [
    {"hook": {"hook": "Stop making bad coffee"}},
    {"hook_regenerator": {"regenerated_hooks": [{"hook": "Stop making bad coffee"}]}},
    {"director": {"scenes": GOOD_SCENES}},
    {"script": {"script": "Line 1. Line 2. Line 3. Line 4. Line 5. " * 5}},
    {"caption": {"captions": [{"caption": "Try this"}]}},
    {"hashtag": {"hashtags": [{"hashtag": "#coffee"}]}},
    {"music": {"scene_music": [{"song_name": "Calm", "why_fits": "slow"}]}},
    {"trend": {"trends": {"posting_time": "8am"}}},
    {"repurpose": {"repurposed_content": {"linkedin": "Post"}}},
    {"collector": {"status": "completed"}},
]


def _with(**override_by_node):
    out = []
    for upd in GOOD_UPDATES:
        node = next(iter(upd))
        out.append({node: override_by_node[node]} if node in override_by_node else upd)
    return out


def _state():
    return {**CreateStoryboardRequest(**VALID_STORYBOARD).model_dump(), "hook": "", "scenes": [], "script": ""}


def _reserve(db, user, credits=5):
    from src.services.storyboard_service import reserve_generation

    user.credits = credits
    db.commit()
    uid = user.id
    sb, job = reserve_generation(db, CreateStoryboardRequest(**VALID_STORYBOARD), uid)
    return uid, sb.id, job.id


def _run(sb_id, job_id, updates=None, side_effect=None, retries_left=None):
    """Run the job function as the worker would, with a scripted graph."""
    from src.ai import graph as graph_module
    from src.services import jobs_services

    rq_job = None if retries_left is None else SimpleNamespace(retries_left=retries_left)
    stream = patch.object(graph_module.graph, "stream",
                          side_effect=side_effect, return_value=iter(updates or GOOD_UPDATES))
    with stream as s, patch.object(jobs_services, "get_current_job", return_value=rq_job):
        try:
            jobs_services.generate_storyboard_job(_state(), sb_id, job_id)
            return None, s
        except Exception as e:  # noqa: BLE001
            return e, s


def _reload(db, *objs):
    db.expire_all()
    return [db.get(type(o), o.id) if not isinstance(o, tuple) else db.get(*o) for o in objs]


def _get(db, model, key):
    db.expire_all()
    return db.get(model, key)


# --------------------------------------------------------------- statuses ----
def test_job_status_values_are_the_single_source_of_truth():
    assert [s.value for s in JobStatus] == ["queued", "running", "completed", "failed", "cancelled"]


# ------------------------------------------------------------- dispatching ----
def _dispatch(db, user, background_tasks=None):
    from src.services import storyboard_service

    user.credits = 5
    db.commit()
    return storyboard_service.create_ai_storyboard(
        db=db, payload=CreateStoryboardRequest(**VALID_STORYBOARD),
        user_id=user.id, background_tasks=background_tasks or MagicMock())


def test_queue_name_is_defined_once_and_used_by_api_and_worker():
    from src.config import jobs as job_config
    from src.services.queue_service import storyboard_queue

    assert storyboard_queue.name == job_config.STORYBOARD_QUEUE_NAME
    with patch("rq.SimpleWorker"):  # the worker module builds a worker at import
        import importlib

        import src.services.worker as worker_module
        importlib.reload(worker_module)
        assert worker_module.QUEUES == [storyboard_queue]


def test_job_is_enqueued_even_with_no_worker_and_reported_as_queued(db, user):
    from src.services import storyboard_service

    bg = MagicMock()
    with patch("rq.Worker.all", return_value=[]):
        result = _dispatch(db, user, bg)
    assert storyboard_service.storyboard_queue.enqueue.called
    assert not bg.add_task.called, "silent in-process fallback must be gone"
    assert result["status"] == "queued"
    assert _get(db, Job, result["job_id"]).status == JobStatus.QUEUED
    assert _get(db, Storyboard, result["storyboard_id"]).status == "queued"


def test_enqueue_sets_timeout_and_bounded_retries(db, user):
    from src.config import jobs as job_config
    from src.services import storyboard_service

    _dispatch(db, user)
    kwargs = storyboard_service.storyboard_queue.enqueue.call_args.kwargs
    assert kwargs["job_timeout"] == job_config.JOB_TIMEOUT_SECONDS
    assert kwargs["retry"].max == job_config.JOB_MAX_RETRIES


def test_in_process_mode_only_when_explicitly_enabled(db, user, monkeypatch):
    from src.config import jobs as job_config
    from src.services import storyboard_service

    monkeypatch.setattr(job_config, "ALLOW_INPROCESS_JOBS", True)
    bg = MagicMock()
    _dispatch(db, user, bg)
    assert bg.add_task.called
    assert not storyboard_service.storyboard_queue.enqueue.called


def test_redis_down_fails_cleanly_with_503_and_refund(db, user):
    from redis.exceptions import ConnectionError as RedisConnectionError

    from src.api.errors import AppError
    from src.services import storyboard_service

    storyboard_service.storyboard_queue.enqueue.side_effect = RedisConnectionError("down")
    with pytest.raises(AppError) as exc:
        _dispatch(db, user)
    assert exc.value.status_code == 503 and exc.value.code == "queue_unavailable"
    job = db.query(Job).one()
    assert _get(db, Job, job.id).status == JobStatus.FAILED
    assert _get(db, Storyboard, job.storyboard_id).status == "failed"
    assert _get(db, User, user.id).credits == 5  # charged then refunded


def test_generate_endpoint_reports_queued(client, auth_headers):
    r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "queued"


# ---------------------------------------------------------------- outcomes ----
def test_success_completes_job_and_storyboard_without_refund(db, user):
    uid, sb_id, job_id = _reserve(db, user)
    err, _ = _run(sb_id, job_id)
    assert err is None
    assert _get(db, Job, job_id).status == JobStatus.COMPLETED
    sb = _get(db, Storyboard, sb_id)
    assert sb.status == "completed" and sb.status_reason is None
    assert _get(db, User, uid).credits == 4


def test_missing_scenes_fail_closed_and_refund(db, user):
    uid, sb_id, job_id = _reserve(db, user)
    err, _ = _run(sb_id, job_id, updates=_with(director={"scenes": [], "scene_error": "timeout"}))
    assert err is None  # final attempt: handled, not re-raised
    assert _get(db, Storyboard, sb_id).status == "failed"
    assert "scene" in _get(db, Storyboard, sb_id).status_reason.lower()
    assert _get(db, Job, job_id).status == JobStatus.FAILED
    assert _get(db, User, uid).credits == 5


def test_missing_script_saves_partial_with_reason_and_refunds(db, user):
    uid, sb_id, job_id = _reserve(db, user)
    _run(sb_id, job_id, updates=_with(script={"script": "", "script_error": "boom"}))
    sb = _get(db, Storyboard, sb_id)
    assert sb.status == "partial"
    assert "script" in sb.status_reason.lower()
    assert db.query(Scene).filter(Scene.storyboard_id == sb_id).count() == 5  # partial results kept
    assert _get(db, Job, job_id).status == JobStatus.COMPLETED
    assert _get(db, User, uid).credits == 5


def test_missing_optional_parts_still_complete_but_say_so(db, user):
    _, sb_id, job_id = _reserve(db, user)
    _run(sb_id, job_id, updates=_with(caption={"captions": []}))
    sb = _get(db, Storyboard, sb_id)
    assert sb.status == "completed"
    assert "caption" in sb.status_reason.lower()


def test_exception_with_retries_left_requeues_without_refund(db, user):
    uid, sb_id, job_id = _reserve(db, user)
    err, _ = _run(sb_id, job_id, side_effect=RuntimeError("provider 500"), retries_left=1)
    assert isinstance(err, RuntimeError), "must re-raise so RQ retries"
    assert _get(db, Job, job_id).status == JobStatus.QUEUED
    assert _get(db, Storyboard, sb_id).status == "queued"
    assert _get(db, User, uid).credits == 4


def test_exception_on_last_attempt_fails_both_with_safe_message_and_refunds(db, user, client):
    uid, sb_id, job_id = _reserve(db, user)
    err, _ = _run(sb_id, job_id, side_effect=RuntimeError("psycopg2 secret internals"), retries_left=0)
    assert isinstance(err, RuntimeError)
    assert _get(db, Job, job_id).status == JobStatus.FAILED
    sb = _get(db, Storyboard, sb_id)
    assert sb.status == "failed"
    assert "internals" not in sb.status_reason
    assert _get(db, User, uid).credits == 5


def test_job_api_shows_user_safe_error(client, auth_headers, db):
    r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers)
    job_id, sb_id = r.json()["job_id"], r.json()["storyboard_id"]
    _run(sb_id, job_id, side_effect=RuntimeError("Traceback psycopg2 internals"), retries_left=0)
    body = client.get(f"/storyboards/jobs/{job_id}", headers=auth_headers).json()
    assert body["status"] == "failed"
    assert "internals" not in (body["error_message"] or "") and body["error_message"]


def test_redelivered_finished_job_is_not_run_again(db, user):
    uid, sb_id, job_id = _reserve(db, user)
    _run(sb_id, job_id)
    err, stream = _run(sb_id, job_id)
    assert err is None and not stream.called
    assert db.query(Scene).filter(Scene.storyboard_id == sb_id).count() == 5
    assert _get(db, User, uid).credits == 4


def test_retry_after_failure_does_not_duplicate_scenes_or_charge_twice(db, user):
    uid, sb_id, job_id = _reserve(db, user)
    from src.repositories.storyboard_repository import save_graph_result

    save_graph_result(db, sb_id, {"scenes": GOOD_SCENES, "script": "x"})  # an earlier attempt's write
    _run(sb_id, job_id)
    assert db.query(Scene).filter(Scene.storyboard_id == sb_id).count() == 5
    assert _get(db, User, uid).credits == 4


# ------------------------------------------------------------------ reaper ----
def _age(db, job_id, created_minutes=0, started_minutes=None, status=None):
    job = db.get(Job, job_id)
    job.created_at = datetime.now(timezone.utc) - timedelta(minutes=created_minutes)
    if started_minutes is not None:
        job.started_at = datetime.now(timezone.utc) - timedelta(minutes=started_minutes)
    if status is not None:
        job.status = status
    db.commit()


def test_reaper_fails_stuck_jobs_refunds_and_leaves_fresh_ones(db, user):
    from src.services.reaper import reap_stuck_jobs

    uid, sb_stuck_q, job_stuck_q = _reserve(db, user, credits=10)
    _, sb_stuck_r, job_stuck_r = _reserve(db, user, credits=9 - 0)
    _age(db, job_stuck_q, created_minutes=120)
    _age(db, job_stuck_r, created_minutes=120, started_minutes=60, status=JobStatus.RUNNING)
    _, sb_fresh, job_fresh = _reserve(db, user, credits=_get(db, User, uid).credits)
    credits_before = _get(db, User, uid).credits

    assert reap_stuck_jobs(db) == 2
    for job_id, sb_id in [(job_stuck_q, sb_stuck_q), (job_stuck_r, sb_stuck_r)]:
        assert _get(db, Job, job_id).status == JobStatus.FAILED
        assert _get(db, Storyboard, sb_id).status == "failed"
    assert _get(db, Job, job_fresh).status == JobStatus.QUEUED
    assert _get(db, User, uid).credits == credits_before + 2
    assert reap_stuck_jobs(db) == 0  # idempotent
    assert _get(db, User, uid).credits == credits_before + 2


# ------------------------------------------------------------ cancellation ----
def test_cancel_queued_job_refunds(client, auth_headers, db):
    r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers)
    job_id, sb_id = r.json()["job_id"], r.json()["storyboard_id"]
    uid = client.get("/auth/me", headers=auth_headers).json()["id"]
    credits = _get(db, User, uid).credits
    with patch("rq.job.Job.fetch", return_value=MagicMock()) as fetch:
        r = client.post(f"/storyboards/jobs/{job_id}/cancel", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    assert fetch.return_value.cancel.called
    assert _get(db, Storyboard, sb_id).status == "cancelled"
    assert _get(db, User, uid).credits == credits + 1


def test_cannot_cancel_running_or_other_users_job(client, auth_headers, db):
    r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers)
    job_id = r.json()["job_id"]
    db.query(Job).filter(Job.id == job_id).update({"status": JobStatus.RUNNING})
    db.commit()
    assert client.post(f"/storyboards/jobs/{job_id}/cancel", headers=auth_headers).status_code == 409

    e = "other@example.com"
    client.post("/auth/register", json={"username": "other", "email": e, "password": STRONG_PASSWORD})
    tok = login_token(client, e, STRONG_PASSWORD)
    assert client.post(f"/storyboards/jobs/{job_id}/cancel",
                       headers={"Authorization": f"Bearer {tok}"}).status_code == 404


_ = asyncio  # keep import for future async tests
