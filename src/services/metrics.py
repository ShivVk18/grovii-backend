"""Prometheus metrics (Phase G).

HTTP latency is measured in this process (each API instance is scraped).
Job, queue, token and cost numbers are computed from Postgres/Redis at scrape
time, because jobs run in separate worker processes.
"""
from prometheus_client import REGISTRY as PROCESS_REGISTRY
from prometheus_client import CollectorRegistry, Gauge, Histogram, generate_latest
from sqlalchemy import text

from src.database import engine

HTTP_LATENCY = Histogram(
    "grovii_http_request_duration_seconds", "API request duration", ["method", "route", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

_JOBS_SQL = text("""
    SELECT status::text AS status, count(*) AS n FROM jobs
    WHERE created_at > now() - interval '24 hours' GROUP BY status
""")
_SPEND_SQL = text("""
    SELECT coalesce(sum(cost_usd), 0), coalesce(sum(prompt_tokens + completion_tokens), 0), coalesce(sum(llm_calls), 0)
    FROM jobs WHERE created_at >= date_trunc('day', now() AT TIME ZONE 'UTC')
""")
_DURATION_SQL = text("""
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM completed_at - started_at)),
           percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM completed_at - started_at))
    FROM jobs WHERE status = 'COMPLETED' AND started_at IS NOT NULL AND completed_at IS NOT NULL
      AND completed_at > now() - interval '24 hours'
""")
_NODE_SQL = text("""
    SELECT key AS node,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY value::float) / 1000.0,
           percentile_cont(0.95) WITHIN GROUP (ORDER BY value::float) / 1000.0
    FROM jobs, jsonb_each_text(node_timings)
    WHERE node_timings IS NOT NULL AND completed_at > now() - interval '24 hours'
    GROUP BY key
""")


def render_metrics() -> bytes:
    reg = CollectorRegistry()
    jobs = Gauge("grovii_jobs", "Jobs created in the last 24h by status", ["status"], registry=reg)
    queue = Gauge("grovii_queue_length", "Jobs waiting in the queue", registry=reg)
    workers = Gauge("grovii_workers", "Workers listening on the queue", registry=reg)
    cost = Gauge("grovii_llm_cost_usd_today", "Estimated LLM spend today (UTC)", registry=reg)
    tokens = Gauge("grovii_llm_tokens_today", "LLM tokens today (UTC)", registry=reg)
    calls = Gauge("grovii_llm_calls_today", "LLM calls today (UTC)", registry=reg)
    duration = Gauge("grovii_job_duration_seconds", "Completed job duration, last 24h", ["quantile"], registry=reg)
    node = Gauge("grovii_job_node_duration_seconds", "Duration per pipeline step, last 24h", ["node", "quantile"], registry=reg)
    failure = Gauge("grovii_job_failure_ratio", "Failed / finished jobs, last 24h", registry=reg)

    with engine.connect() as conn:
        counts = {row.status.lower(): row.n for row in conn.execute(_JOBS_SQL)}
        for status in ("queued", "running", "completed", "failed", "cancelled"):
            jobs.labels(status).set(counts.get(status, 0))
        finished = counts.get("completed", 0) + counts.get("failed", 0)
        failure.set(counts.get("failed", 0) / finished if finished else 0)
        c, t, n = conn.execute(_SPEND_SQL).one()
        cost.set(float(c or 0))
        tokens.set(float(t or 0))
        calls.set(float(n or 0))
        p50, p95 = conn.execute(_DURATION_SQL).one()
        duration.labels("0.5").set(float(p50 or 0))
        duration.labels("0.95").set(float(p95 or 0))
        for row in conn.execute(_NODE_SQL):
            node.labels(row[0], "0.5").set(float(row[1] or 0))
            node.labels(row[0], "0.95").set(float(row[2] or 0))
    try:
        from src.api.ops import queue_length, worker_count

        queue.set(queue_length())
        workers.set(worker_count())
    except Exception:  # noqa: BLE001 - Redis down: report -1
        queue.set(-1)
        workers.set(-1)
    return generate_latest(reg) + generate_latest(PROCESS_REGISTRY)
