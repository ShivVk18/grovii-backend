"""Health, readiness and metrics (Phase G).

/health       liveness: the process answers. No dependencies, never slow.
/ready        readiness: database, Redis and schema version are OK. 503 otherwise,
              so the platform keeps traffic on the old version during a deploy.
/health/deep  for monitors: readiness plus "is any worker running" and queue size.
/metrics      Prometheus text; needs METRICS_TOKEN. Job numbers come from the
              database, so they are correct no matter which process ran the job.

Responses say only ok/not ok: no hostnames, URLs or error text.
"""
import hmac
import logging
import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from src.config import ops_settings
from src.database import engine

logger = logging.getLogger("grovii.ops")
router = APIRouter(tags=["Ops"])

ROOT = Path(__file__).resolve().parents[2]


def check_database() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def current_db_revision() -> str | None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).first()
    return row[0] if row else None


@lru_cache(maxsize=1)
def head_revision() -> str | None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def check_redis() -> bool:
    from src.services.redis_service import redis_client

    return bool(redis_client.ping())


def worker_count() -> int:
    from rq import Worker

    from src.services.queue_service import storyboard_queue
    from src.services.redis_service import redis_client

    return len(Worker.all(connection=redis_client, queue=storyboard_queue))


def queue_length() -> int:
    from src.services.queue_service import storyboard_queue

    return int(storyboard_queue.count)


def _run(name: str, fn) -> dict:
    start = time.perf_counter()
    try:
        ok = bool(fn())
    except Exception as e:  # noqa: BLE001 - report, never raise
        logger.warning("Readiness check %s failed: %s", name, type(e).__name__)
        ok = False
    return {"ok": ok, "ms": round((time.perf_counter() - start) * 1000, 1)}


def _readiness() -> dict:
    checks = {"database": _run("database", check_database), "redis": _run("redis", check_redis)}

    def migrations_ok() -> bool:
        return current_db_revision() == head_revision()

    checks["migrations"] = _run("migrations", migrations_ok) if checks["database"]["ok"] else {"ok": False}
    return checks


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    checks = _readiness()
    ok = all(c["ok"] for c in checks.values())
    return JSONResponse({"status": "ok" if ok else "unavailable", "checks": checks}, status_code=200 if ok else 503)


@router.get("/health/deep")
def deep_health():
    checks = _readiness()
    try:
        workers = worker_count()
    except Exception:  # noqa: BLE001
        workers = 0
    try:
        length = queue_length()
    except Exception:  # noqa: BLE001
        length = -1
    checks["workers"] = {"ok": workers > 0, "count": workers}
    checks["queue"] = {"ok": length >= 0, "length": length}
    ok = all(c["ok"] for c in checks.values())
    return JSONResponse({"status": "ok" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503)


@router.get("/metrics", include_in_schema=False)
def metrics(request: Request):
    token = ops_settings.METRICS_TOKEN
    if not token:
        return Response(status_code=404)
    presented = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(presented, token):
        return Response(status_code=401)
    from src.services.metrics import render_metrics

    return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")
