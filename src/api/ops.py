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
def _scripts():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return ScriptDirectory.from_config(cfg)


def head_revision() -> str | None:
    return _scripts().get_current_head()


def migration_state() -> dict:
    """ok when the database is at this code's head, or AHEAD of it (a newer
    release already migrated; old instances keep serving during a deploy and
    after an app-only rollback). Not ok when the database is behind the code."""
    db_rev = current_db_revision()
    head = head_revision()
    if db_rev == head:
        return {"ok": True}
    known = {rev.revision for rev in _scripts().walk_revisions()}
    if db_rev and db_rev not in known:
        return {"ok": True, "note": "database is newer than this release"}
    return {"ok": False, "note": "database needs `alembic upgrade head`"}


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

    if checks["database"]["ok"]:
        try:
            checks["migrations"] = migration_state()
        except Exception as e:  # noqa: BLE001
            logger.warning("Readiness check migrations failed: %s", type(e).__name__)
            checks["migrations"] = {"ok": False}
    else:
        checks["migrations"] = {"ok": False}
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
