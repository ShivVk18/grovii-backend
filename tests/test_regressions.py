"""Regression tests for bugs confirmed in eval/FINAL_REPORT.md.

Each test asserts the CORRECT behaviour. While a bug is unfixed the test is
marked `xfail(strict=True)`: it must fail, and if it starts passing pytest
reports XPASS as an error, which tells the fixing phase to remove the marker.

Frontend bugs (FE-01 hardcoded repurpose, FE-03 music `reason`) are covered in
frontend/tests/regressions.test.mjs.
"""
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.models.jobs import Job, JobStatus
from src.models.storyboard import Storyboard
from src.Schemas.storyboard_schema import CreateStoryboardRequest
from tests.conftest import VALID_STORYBOARD

pytestmark = pytest.mark.regression


def _make_storyboard_and_job(db, user):
    sb = Storyboard(user_id=user.id, idea="x", goal="g", tone="t", style="s",
                    audience="a", duration=30, platform="p", status="pending")
    db.add(sb)
    db.commit()
    job = Job(user_id=user.id, storyboard_id=sb.id)
    db.add(job)
    db.commit()
    return sb.id, job.id


def _state():
    return dict(CreateStoryboardRequest(**VALID_STORYBOARD).model_dump(), hook="", scenes=[], script="")


# ---------------------------------------------------------------- OPS-01 ----
# OPS-01 fixed in Phase C.
def test_ops01_job_goes_to_redis_when_a_worker_listens_on_the_real_queue(db, user):
    """A live worker on the `storyboards` queue exists, so the job must be enqueued
    to Redis, not run in-process via BackgroundTasks."""
    from src.services import storyboard_service
    from src.services.queue_service import storyboard_queue
    from src.services.redis_service import redis_client

    worker = MagicMock()
    worker.queues = [storyboard_queue]  # the queue the real worker listens on
    worker.get_state.return_value = "idle"
    background_tasks = MagicMock()

    with patch.object(redis_client, "ping", return_value=True), \
         patch("rq.Worker.all", return_value=[worker]), \
         patch.object(storyboard_service.storyboard_queue, "enqueue", return_value=MagicMock(id="rq-1")) as enqueue:
        storyboard_service.create_ai_storyboard(
            db=db, payload=CreateStoryboardRequest(**VALID_STORYBOARD),
            user_id=user.id, background_tasks=background_tasks)

    assert enqueue.called, "job was not enqueued to Redis"
    assert not background_tasks.add_task.called, "job silently fell back to in-process execution"


# ---------------------------------------------------------------- API-01 ----
def test_api01_jobs_list_route_is_reachable(client, auth_headers):
    r = client.get("/storyboards/jobs", headers=auth_headers)
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------- RES-01 ----
# RES-01 fixed in Phase C.
def test_res01_failed_job_marks_storyboard_failed(db, user):
    from src.ai import graph as graph_module
    from src.services.jobs_services import generate_storyboard_job

    sb_id, job_id = _make_storyboard_and_job(db, user)
    with patch.object(graph_module.graph, "stream", side_effect=RuntimeError("LLM provider down")):
        with pytest.raises(RuntimeError):
            generate_storyboard_job(_state(), sb_id, job_id)

    db.expire_all()
    assert db.get(Job, job_id).status == JobStatus.FAILED  # this part already works
    assert db.get(Storyboard, sb_id).status == "failed"


# ---------------------------------------------------------------- RES-02 ----
def test_res02_precondition_scene_node_swallows_errors_into_empty_list():
    """Documents the trigger for RES-02: on any LLM error, scene_node returns []
    instead of raising. (Passes today; it proves the bug path exists.)"""
    from src.ai.nodes import scene_node as mod

    with patch.object(mod.openai_service, "get_llm", side_effect=RuntimeError("timeout")):
        out = mod.scene_node(_state())
    assert out["scenes"] == []
    assert "timeout" in out["scene_error"]


# RES-02 fixed in Phase C.
def test_res02_empty_scenes_never_saved_as_completed(db, user):
    from src.ai import graph as graph_module
    from src.services.jobs_services import generate_storyboard_job

    sb_id, job_id = _make_storyboard_and_job(db, user)
    updates = [
        {"hook": {"hook": "A hook"}},
        {"director": {"scenes": [], "scene_error": "timeout"}},  # what scene_node returns on failure
        {"script": {"script": "Some script"}},
        {"collector": {"status": "completed"}},
    ]
    with patch.object(graph_module.graph, "stream", return_value=iter(updates)):
        try:
            generate_storyboard_job(_state(), sb_id, job_id)
        except Exception:
            pass  # raising is an acceptable way to fail closed

    db.expire_all()
    assert db.get(Storyboard, sb_id).status != "completed"
    assert db.get(Job, job_id).status != JobStatus.COMPLETED


# ---------------------------------------------------------------- VAL-01 ----
BAD_INPUTS = [
    ("idea", ""),
    ("idea", "     "),
    ("idea", "x" * 10_001),
    ("duration", -5),
    ("duration", 0),
    ("duration", 100_000),
    ("platform", ""),
    ("tone", "   "),
]


# VAL-01 fixed in Phase B (see tests/test_validation.py for full boundary coverage).
@pytest.mark.parametrize("field,value", BAD_INPUTS, ids=[f"{f}={str(v)[:12]!r}" for f, v in BAD_INPUTS])
def test_val01_create_request_rejects_bad_input(field, value):
    with pytest.raises(ValidationError):
        CreateStoryboardRequest(**{**VALID_STORYBOARD, field: value})


def test_val01_valid_input_still_accepted():
    CreateStoryboardRequest(**VALID_STORYBOARD)
