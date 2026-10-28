"""Phase B: LLM safety limits (timeouts, output caps, per-job token budget,
daily spend ceiling) and per-job usage/cost recording."""
import itertools
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.config import limits
from src.models.jobs import Job, JobStatus
from src.models.storyboard import Storyboard
from src.models.users import User
from tests.conftest import VALID_STORYBOARD

PROMPT_TOKENS, COMPLETION_TOKENS = 100, 50
GRAPH_LLM_NODES = {"hook", "hook_regenerator", "director", "script", "caption",
                   "hashtag", "music", "trend", "repurpose"}


@pytest.fixture
def fake_llm():
    """Replace the real OpenAI client with a fake that reports fixed token usage,
    keeping everything else get_llm() sets up (callbacks, node name)."""
    from src.services import openai_service as mod

    built: list[dict] = []

    def fake_chat_model(**kwargs):
        built.append(kwargs)
        reply = AIMessage(content="{}", usage_metadata={
            "input_tokens": PROMPT_TOKENS, "output_tokens": COMPLETION_TOKENS,
            "total_tokens": PROMPT_TOKENS + COMPLETION_TOKENS})
        return GenericFakeChatModel(messages=itertools.repeat(reply), callbacks=kwargs.get("callbacks"))

    with patch.object(mod, "_chat_model", side_effect=fake_chat_model):
        yield built


def _state():
    return {**VALID_STORYBOARD, "hook": "", "scenes": [], "script": ""}


def _run_graph():
    from src.ai.graph import graph

    for _ in graph.stream(_state(), stream_mode="updates"):
        pass


# ------------------------------------------------------------ per-node caps ----
def test_get_llm_sets_timeout_retries_and_per_node_output_cap():
    from src.services.openai_service import openai_service

    director = openai_service.get_llm("director")
    hook = openai_service.get_llm("hook")
    unknown = openai_service.get_llm("something_new")

    assert director.max_output_tokens == limits.NODE_MAX_OUTPUT_TOKENS["director"]
    assert hook.max_output_tokens == limits.NODE_MAX_OUTPUT_TOKENS["hook"]
    assert unknown.max_output_tokens == limits.DEFAULT_MAX_OUTPUT_TOKENS
    for llm in (director, hook, unknown):
        assert llm.timeout == limits.LLM_TIMEOUT_SECONDS
        assert llm.max_retries == limits.LLM_MAX_RETRIES


def test_every_graph_node_has_an_output_cap():
    from src.ai.graph import graph

    llm_nodes = set(graph.nodes) - {"__start__", "collector"}
    assert llm_nodes == GRAPH_LLM_NODES
    assert llm_nodes <= set(limits.NODE_MAX_OUTPUT_TOKENS)


def test_every_node_identifies_itself_to_get_llm(fake_llm):
    from src.services.llm_usage import metered

    with metered(budget=1_000_000):
        _run_graph()
    assert {k["node"] for k in fake_llm} == GRAPH_LLM_NODES


# ---------------------------------------------------------------- timeouts ----
class _StallingHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # never answers in time
        time.sleep(5)

    def log_message(self, *args):
        pass


def test_a_hanging_provider_times_out_instead_of_blocking_forever(monkeypatch):
    """Real HTTP: a local server that never answers. The call must fail after
    roughly timeout x (1 + retries), not hang."""
    from src.services.openai_service import openai_service

    server = ThreadingHTTPServer(("127.0.0.1", 0), _StallingHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(limits, "LLM_TIMEOUT_SECONDS", 0.5)
    monkeypatch.setattr(limits, "LLM_MAX_RETRIES", 1)
    monkeypatch.setattr(limits, "LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    try:
        started = time.monotonic()
        with pytest.raises(Exception) as exc:  # provider-specific type (httpx/openai/google)
            openai_service.get_llm("hook").invoke("hello")
        elapsed = time.monotonic() - started
        assert "timeout" in type(exc.value).__name__.lower() or "timed out" in str(exc.value).lower(), exc.value
    finally:
        server.shutdown()
    assert elapsed < 4, f"took {elapsed:.1f}s"


# ---------------------------------------------------------------- metering ----
def test_usage_from_all_parallel_nodes_is_metered(fake_llm):
    from src.services.llm_usage import metered

    with metered(budget=1_000_000) as meter:
        _run_graph()

    assert set(meter.by_node) == GRAPH_LLM_NODES  # includes the 5 fan-out nodes running in threads
    assert meter.calls >= len(GRAPH_LLM_NODES)
    assert meter.prompt_tokens == PROMPT_TOKENS * meter.calls
    assert meter.completion_tokens == COMPLETION_TOKENS * meter.calls
    assert meter.cost_usd == pytest.approx(limits.estimate_cost_usd(meter.prompt_tokens, meter.completion_tokens))


def test_token_budget_stops_further_llm_calls(fake_llm):
    from src.services.llm_usage import metered

    per_call = PROMPT_TOKENS + COMPLETION_TOKENS
    # hook (150) + hook_regenerator (300) + director (450): the 4th call sees
    # 450 >= 320 and is refused before it is sent.
    from src.services.llm_usage import BudgetExceeded

    with metered(budget=320) as meter:
        try:
            _run_graph()
        except BudgetExceeded:
            pass  # nodes without their own try/except (trend) let it propagate; either way calls stop

    assert meter.exceeded
    assert meter.calls == 3
    assert meter.total_tokens == 3 * per_call


# --------------------------------------------------- recorded on the job row ----
def _job(db, user, credits_charged=1):
    sb = Storyboard(user_id=user.id, idea="x" * 10, goal="educate", tone="calm", style="pov",
                    audience="ab", duration=30, platform="reels", status="pending")
    db.add(sb)
    db.flush()
    job = Job(user_id=user.id, storyboard_id=sb.id, credits_charged=credits_charged)
    db.add(job)
    db.commit()
    return sb.id, job.id


def test_job_records_tokens_calls_and_cost(fake_llm, db, user):
    from src.services.jobs_services import generate_storyboard_job

    sb_id, job_id = _job(db, user)
    generate_storyboard_job(_state(), sb_id, job_id)

    db.expire_all()
    job = db.get(Job, job_id)
    assert job.llm_calls >= len(GRAPH_LLM_NODES)
    assert job.prompt_tokens == PROMPT_TOKENS * job.llm_calls
    assert job.completion_tokens == COMPLETION_TOKENS * job.llm_calls
    assert float(job.cost_usd) == pytest.approx(
        limits.estimate_cost_usd(job.prompt_tokens, job.completion_tokens), abs=1e-6)


def test_budget_exceeded_fails_the_job_refunds_and_still_records_usage(fake_llm, db, user, monkeypatch):
    from src.services.jobs_services import generate_storyboard_job

    monkeypatch.setattr(limits, "JOB_TOKEN_BUDGET", 320)
    user.credits = 4
    db.commit()
    sb_id, job_id = _job(db, user)

    # Handled without raising: a retry would hit the same budget, so RQ must not retry.
    assert generate_storyboard_job(_state(), sb_id, job_id) is None

    db.expire_all()
    job = db.get(Job, job_id)
    assert job.status == JobStatus.FAILED
    assert "token budget" in job.error_message
    assert job.llm_calls == 3 and job.prompt_tokens == 300
    assert job.credits_refunded is True
    assert db.get(User, user.id).credits == 5


# ------------------------------------------------------ daily spend ceiling ----
def _spent_today(db, user, usd, status=JobStatus.COMPLETED):
    sb = Storyboard(user_id=user.id, idea="x" * 10, goal="educate", tone="calm", style="pov",
                    audience="ab", duration=30, platform="reels", status="completed")
    db.add(sb)
    db.flush()
    db.add(Job(user_id=user.id, storyboard_id=sb.id, status=status, cost_usd=usd))
    db.commit()


def test_daily_ceiling_refuses_new_jobs_with_503_and_alerts(client, auth_headers, db, user, monkeypatch, caplog):
    monkeypatch.setattr(limits, "DAILY_SPEND_LIMIT_USD", 1.00)
    _spent_today(db, user, 0.99)  # another user's spend counts too: the ceiling is global
    uid = client.get("/auth/me", headers=auth_headers).json()["id"]

    with caplog.at_level(logging.CRITICAL, logger="grovii.spend"):
        r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers)

    assert r.status_code == 503, r.text
    assert r.json()["code"] == "daily_limit_reached"
    assert "$" not in r.json()["detail"]  # no internal numbers shown to users
    assert any("ALERT" in rec.message and "daily spend" in rec.message for rec in caplog.records)
    db.expire_all()
    assert db.get(User, uid).credits == 100  # not charged


def test_in_flight_jobs_are_reserved_against_the_ceiling(client, auth_headers, db, user, monkeypatch):
    monkeypatch.setattr(limits, "DAILY_SPEND_LIMIT_USD", limits.JOB_COST_RESERVE_USD * 2.5)
    _spent_today(db, user, None, status=JobStatus.RUNNING)
    _spent_today(db, user, None, status=JobStatus.QUEUED)
    # 2 reserved + this one = 3 x reserve > 2.5 x reserve
    r = client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers)
    assert r.status_code == 503


def test_yesterdays_spend_does_not_count(client, auth_headers, db, user, monkeypatch):
    monkeypatch.setattr(limits, "DAILY_SPEND_LIMIT_USD", 1.00)
    _spent_today(db, user, 5.00)
    db.query(Job).update({"created_at": datetime.now(timezone.utc) - timedelta(days=1, hours=1)})
    db.commit()
    assert client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers).status_code == 200


def test_under_the_ceiling_generation_proceeds(client, auth_headers, db, user, monkeypatch):
    monkeypatch.setattr(limits, "DAILY_SPEND_LIMIT_USD", 20.0)
    _spent_today(db, user, 1.00)
    assert client.post("/storyboards/generate", json=VALID_STORYBOARD, headers=auth_headers).status_code == 200


def test_usage_accumulates_across_retry_attempts(db, user):
    """Each RQ attempt records its own usage; retries must add, not overwrite."""
    from src.services.llm_usage import UsageMeter
    from src.services.spend_service import record_job_usage

    _, job_id = _job(db, user)
    for _ in range(3):  # 3 attempts
        m = UsageMeter(budget=10**6)
        m.add("hook", PROMPT_TOKENS, COMPLETION_TOKENS)
        record_job_usage(db, job_id, m)

    db.expire_all()
    job = db.get(Job, job_id)
    assert job.llm_calls == 3
    assert job.prompt_tokens == 3 * PROMPT_TOKENS
    assert job.completion_tokens == 3 * COMPLETION_TOKENS
    assert float(job.cost_usd) == pytest.approx(limits.estimate_cost_usd(3 * PROMPT_TOKENS, 3 * COMPLETION_TOKENS), abs=1e-6)
