"""Phase G: production operations (health, logs, metrics, alerts, errors)."""
import json
import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.jobs import Job, JobStatus
from src.models.storyboard import Storyboard


def _app():
    from src.main import app

    return app


# ------------------------------------------------------------ migrations ----

def test_api_startup_does_not_change_the_schema():
    """Schema changes happen only through Alembic (a deploy step), never at app start."""
    from src.database import Base

    with patch.object(Base.metadata, "create_all") as create_all, patch("src.database.engine.connect") as connect:
        with TestClient(_app()):
            pass
    create_all.assert_not_called()
    for call in connect.return_value.__enter__.return_value.execute.call_args_list:
        assert "ALTER TABLE" not in str(call.args[0]).upper()


# --------------------------------------------------------------- health -----

def test_health_is_cheap_and_always_up():
    with patch("src.api.ops.check_database", side_effect=AssertionError("must not touch the DB")):
        r = TestClient(_app()).get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_ready_checks_database_redis_and_migrations():
    r = TestClient(_app()).get("/ready")
    assert r.status_code == 200, r.text
    checks = r.json()["checks"]
    assert checks["database"]["ok"] and checks["redis"]["ok"] and checks["migrations"]["ok"]


def test_ready_is_503_when_redis_is_down():
    from src.services.redis_service import redis_client

    with patch.object(redis_client, "ping", side_effect=ConnectionError("down")):
        r = TestClient(_app()).get("/ready")
    assert r.status_code == 503 and r.json()["checks"]["redis"]["ok"] is False


def test_ready_is_503_when_the_database_is_behind_the_code():
    with patch("src.api.ops.current_db_revision", return_value="0000000000"):
        r = TestClient(_app()).get("/ready")
    assert r.status_code == 503 and r.json()["checks"]["migrations"]["ok"] is False


def test_deep_health_reports_workers_and_queue():
    with patch("src.api.ops.worker_count", return_value=0):
        r = TestClient(_app()).get("/health/deep")
    body = r.json()
    assert r.status_code == 503 and body["checks"]["workers"]["count"] == 0
    assert "length" in body["checks"]["queue"]
    with patch("src.api.ops.worker_count", return_value=2):
        assert TestClient(_app()).get("/health/deep").status_code == 200


def test_health_endpoints_leak_no_internals():
    from src.services.redis_service import redis_client

    with patch.object(redis_client, "ping", side_effect=ConnectionError("redis://:hunter2@10.0.0.3:6379 refused")):
        r = TestClient(_app()).get("/ready")
    assert "hunter2" not in r.text and "10.0.0.3" not in r.text


# ------------------------------------------------- request id + JSON logs ---

def test_request_id_is_returned_and_generated_when_missing():
    c = TestClient(_app())
    rid = c.get("/health").headers["x-request-id"]
    assert len(rid) >= 16
    assert c.get("/health", headers={"X-Request-ID": "abc-123-def-456"}).headers["x-request-id"] == "abc-123-def-456"
    # Junk ids are replaced, not echoed (log injection).
    bad = c.get("/health", headers={"X-Request-ID": "x\nFAKE LOG LINE"}).headers["x-request-id"]
    assert "\n" not in bad and "FAKE" not in bad


def test_json_log_lines_carry_the_request_id():
    from src.config.logging_config import JsonFormatter, request_id_var

    token = request_id_var.set("req-42")
    try:
        record = logging.LogRecord("grovii.test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
        line = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert line["msg"] == "hello world" and line["request_id"] == "req-42"
    assert line["level"] == "INFO" and line["logger"] == "grovii.test" and "ts" in line


def test_request_id_travels_into_the_job(client, auth_headers):
    from src.services import storyboard_service
    from tests.conftest import VALID_STORYBOARD

    r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers={**auth_headers, "X-Request-ID": "trace-me-123456"})
    assert r.status_code == 200, r.text
    kwargs = storyboard_service.storyboard_queue.enqueue.call_args.kwargs  # mocked by conftest
    assert kwargs.get("meta", {}).get("request_id") == "trace-me-123456"


# ------------------------------------------------------- job summary log ----

def _job(db, user):
    sb = Storyboard(user_id=user.id, idea="x" * 20, goal="educate", tone="calm", style="talking_head",
                    audience="x", duration=30, platform="reels", status="queued")
    db.add(sb)
    db.flush()
    job = Job(user_id=user.id, storyboard_id=sb.id, status=JobStatus.QUEUED, progress=0, credits_charged=1)
    db.add(job)
    db.commit()
    return sb, job


def test_finished_job_logs_one_summary_with_duration_nodes_and_cost(db, user, caplog):
    from src.ai import graph as graph_module
    from src.services.jobs_services import generate_storyboard_job

    sb, job = _job(db, user)
    fake = MagicMock()
    fake.stream.return_value = iter([
        {"hook": {"hook": "Hook"}},
        {"director": {"scenes": [{"scene_number": 1, "duration": "30", "voiceover_example": "Hi"}]}},
        {"script": {"script": "Hi"}},
    ])
    caplog.set_level(logging.INFO)
    with patch.object(graph_module, "graph", fake):
        generate_storyboard_job({"idea": "x", "language": "English"}, sb.id, job.id)
    summaries = [r for r in caplog.records if getattr(r, "event", None) == "job_finished"]
    assert len(summaries) == 1
    s = summaries[0]
    assert s.status == "completed" and s.duration_ms >= 0
    assert set(s.node_ms) >= {"hook", "director", "script"}
    assert hasattr(s, "cost_usd") and hasattr(s, "tokens")
    db.expire_all()
    assert set(db.get(Job, job.id).node_timings) >= {"hook", "director", "script"}


# ---------------------------------------------------------------- metrics ---

def test_metrics_need_a_token_and_expose_job_and_queue_numbers(monkeypatch, db, user):
    from src.config import ops_settings

    _job(db, user)
    monkeypatch.setattr(ops_settings, "METRICS_TOKEN", "metrics-secret-123")
    c = TestClient(_app())
    assert c.get("/metrics").status_code == 401
    r = c.get("/metrics", headers={"Authorization": "Bearer metrics-secret-123"})
    assert r.status_code == 200
    text = r.text
    for name in ("grovii_queue_length", "grovii_jobs", "grovii_llm_cost_usd_today", "grovii_llm_tokens_today",
                 "grovii_job_duration_seconds", "grovii_http_request_duration_seconds"):
        assert name in text, name


def test_metrics_disabled_without_a_token(monkeypatch):
    from src.config import ops_settings

    monkeypatch.setattr(ops_settings, "METRICS_TOKEN", "")
    assert TestClient(_app()).get("/metrics").status_code == 404


# ----------------------------------------------------------------- alerts ---

def test_alerts_fire_for_failure_spike_backlog_and_spend(db, user, monkeypatch, caplog):
    from src.config import ops_settings
    from src.services import ops_alerts

    monkeypatch.setattr(ops_settings, "ALERT_FAILED_JOBS", 2)
    monkeypatch.setattr(ops_settings, "ALERT_QUEUE_BACKLOG", 0)
    for _ in range(3):
        _, job = _job(db, user)
        job.status = JobStatus.FAILED
    db.commit()
    sent = []
    monkeypatch.setattr(ops_alerts, "_post_webhook", lambda text: sent.append(text))
    monkeypatch.setattr(ops_settings, "ALERT_WEBHOOK_URL", "https://hooks.example/test")
    with patch("src.services.ops_alerts.queue_length", return_value=5), \
         patch("src.services.ops_alerts.spend_fraction", return_value=0.95):
        caplog.set_level(logging.WARNING)
        fired = ops_alerts.check_and_alert()
    assert {"failed_jobs", "queue_backlog", "spend"} <= set(fired)
    assert any("ALERT" in r.getMessage() and r.levelno == logging.CRITICAL for r in caplog.records)
    assert len(sent) == 3
    # Same alerts again right away are deduplicated (no paging storm).
    with patch("src.services.ops_alerts.queue_length", return_value=5), \
         patch("src.services.ops_alerts.spend_fraction", return_value=0.95):
        assert ops_alerts.check_and_alert() == []


# ----------------------------------------------------------------- sentry ---

def test_sentry_is_off_without_dsn_and_scrubs_personal_data(monkeypatch):
    from src.config import observability

    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert observability.init_sentry() is False
    event = {
        "request": {"cookies": {"grovii_session": "eyJ.secret.token"}, "data": {"idea": "my private idea", "password": "pw"},
                    "headers": {"Authorization": "Bearer abc", "Cookie": "grovii_session=x", "User-Agent": "UA"}},
        "user": {"email": "a@example.com", "id": "u1"},
        "extra": {"prompt": "full prompt with idea"},
    }
    clean = observability.scrub_event(event, None)
    text = json.dumps(clean)
    for secret in ("eyJ.secret.token", "my private idea", "Bearer abc", "grovii_session=x", "a@example.com", "full prompt"):
        assert secret not in text, secret
    assert clean["user"] == {"id": "u1"}


# ---------------------------------------------------- provider outage msg ---

@pytest.mark.parametrize("error", [
    "ServerError: 503 UNAVAILABLE. The model is overloaded.",
    "ResourceExhausted: 429 Quota exceeded",
    "ReadTimeout: timed out",
    "ConnectError: [Errno 61] Connection refused",
])
def test_provider_outage_gets_its_own_message(db, user, error, monkeypatch):
    from src.ai import graph as graph_module
    from src.services import jobs_services
    from src.services.job_lifecycle import USER_MESSAGES

    monkeypatch.setattr(jobs_services, "_retries_left", lambda: 0)
    sb, job = _job(db, user)
    fake = MagicMock()
    fake.stream.return_value = iter([{"director": {"scenes": [], "scene_error": error}}])
    with patch.object(graph_module, "graph", fake):
        jobs_services.generate_storyboard_job({"idea": "x"}, sb.id, job.id)
    db.expire_all()
    j = db.get(Job, job.id)
    assert j.status == JobStatus.FAILED and j.credits_refunded
    from src.services.job_lifecycle import user_message_for
    msg = user_message_for(j, db.get(Storyboard, sb.id))
    assert msg == USER_MESSAGES["provider_down"]
    assert "AI provider" in msg and "refunded" in msg


def test_unique_request_ids():
    c = TestClient(_app())
    ids = {c.get("/health").headers["x-request-id"] for _ in range(5)}
    assert len(ids) == 5
    _ = uuid  # keep import
