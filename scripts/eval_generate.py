"""Generate the Phase 5 eval set through the real product path (REAL LLM calls).

For each of the 10 eval inputs x N runs: reserve (charge) -> run the worker job
function -> save to the DB -> read back through StoryboardDetailResponse (what
the frontend receives) -> write a file in the format eval/tools/run_phase5_validators.py
expects. Also records latency, tokens and cost per run.

Needs a migrated database whose name ends in _test (DATABASE_URL), e.g.:
    python scripts/eval_generate.py --out ../fix/evidence/phase_d/run_before --runs 3
"""
import argparse
import concurrent.futures as cf
import glob
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.engine import make_url  # noqa: E402

if not (make_url(os.environ["DATABASE_URL"]).database or "").endswith("_test"):
    sys.exit("Refusing: DATABASE_URL must point at a database whose name ends in _test")

from src.database import SessionLocal  # noqa: E402
from src.models.jobs import Job  # noqa: E402
from src.models.users import User  # noqa: E402
from src.repositories.storyboard_repository import get_storyboard_with_relations  # noqa: E402
from src.Schemas.storyboard_schema import (  # noqa: E402
    CreateStoryboardRequest,
    StoryboardDetailResponse,
)
from src.services.jobs_services import generate_storyboard_job  # noqa: E402
from src.services.storyboard_service import _job_state, reserve_generation  # noqa: E402

EVAL_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "data")
# Eval inputs with free-text values the Phase B validation does not accept.
VALUE_MAP = {"Emotional but authentic": "emotional"}
FIELDS = ("idea", "goal", "tone", "style", "audience", "duration", "platform", "language")


def load_cases():
    cases = []
    for path in sorted(glob.glob(os.path.join(EVAL_DATA, "T*_run1.json")), key=lambda p: int(p.split("/T")[-1].split("_")[0])):
        d = json.load(open(path))
        raw = {k: VALUE_MAP.get(d[k], d[k]) for k in FIELDS}
        cases.append((d["test_case_id"], CreateStoryboardRequest(**raw)))
    return cases


def to_validator_format(case_id, run, detail: dict, meta: dict) -> dict:
    music = detail.get("music") or []
    return {
        "test_case_id": case_id, "run_number": run,
        **{k: detail.get(k) for k in FIELDS},
        "title": detail.get("title"), "status": detail.get("status"),
        "status_reason": detail.get("status_reason"),
        "hook": detail.get("hook"), "script": detail.get("script"),
        "scenes": detail.get("scenes") or [],
        "hooks": [h["hook"] for h in detail.get("hooks") or []],
        "captions": [c["caption"] for c in detail.get("captions") or []],
        "hashtags": [h["hashtag"] for h in detail.get("hashtags") or []],
        "music": music[0] if music else {},
        "music_all": music,
        "repurpose": detail.get("repurpose") or {},
        "_meta": meta,
    }


def new_user() -> str:
    db = SessionLocal()
    try:
        user = User(username=f"eval_{uuid.uuid4().hex[:8]}", email=f"eval_{uuid.uuid4().hex[:8]}@example.com",
                    hashed_password="x", credits=10_000)
        db.add(user)
        db.commit()
        return user.id
    finally:
        db.close()


def run_with_retries(case_id, payload, run, attempts=3):
    """Re-run a storyboard that failed for provider reasons (429/503/504), up to
    `attempts` times; every attempt is recorded in _meta.attempts."""
    history = []
    for i in range(1, attempts + 1):
        sb = run_one(new_user(), case_id, payload, run)
        history.append({"attempt": i, "status": sb["status"], "error": sb["_meta"]["error"]})
        if sb["status"] in ("completed", "partial"):
            break
        time.sleep(30)
    sb["_meta"]["attempts"] = history
    return sb


def run_one(user_id, case_id, payload, run):
    db = SessionLocal()
    try:
        sb, job = reserve_generation(db, payload, user_id)
        sb_id, job_id = sb.id, job.id
    finally:
        db.close()
    started = time.monotonic()
    error = None
    try:
        generate_storyboard_job(_job_state(payload), sb_id, job_id)
    except Exception as e:  # noqa: BLE001 - record and continue
        error = f"{type(e).__name__}: {str(e)[:300]}"
    elapsed = round(time.monotonic() - started, 1)
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        sb = get_storyboard_with_relations(db, sb_id, user_id)
        detail = json.loads(StoryboardDetailResponse.model_validate(sb).model_dump_json())
        detail["status_reason"] = sb.status_reason
        meta = {"seconds": elapsed, "job_status": job.status.value, "error": error,
                "llm_calls": job.llm_calls, "prompt_tokens": job.prompt_tokens,
                "completion_tokens": job.completion_tokens, "cost_usd": float(job.cost_usd or 0)}
    finally:
        db.close()
    return to_validator_format(case_id, run, detail, meta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--cases", default="", help="comma list like T1,T6 (default all)")
    args = ap.parse_args()

    out_dir = os.path.join(args.out, "eval", "data")
    os.makedirs(out_dir, exist_ok=True)
    cases = [c for c in load_cases() if not args.cases or c[0] in args.cases.split(",")]

    tasks = [(cid, payload, r) for cid, payload in cases for r in range(1, args.runs + 1)]
    with cf.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(run_with_retries, cid, p, r): (cid, r) for cid, p, r in tasks}
        for fut in cf.as_completed(futures):
            cid, r = futures[fut]
            sb = fut.result()
            with open(os.path.join(out_dir, f"{cid}_run{r}.json"), "w") as f:
                json.dump(sb, f, ensure_ascii=False, indent=2)
            m = sb["_meta"]
            print(f"{cid} run{r}: attempts={len(m['attempts'])} {m['job_status']} storyboard={sb['status']} {m['seconds']}s "
                  f"calls={m['llm_calls']} tokens={m['prompt_tokens']}/{m['completion_tokens']} "
                  f"${m['cost_usd']:.4f} {m['error'] or ''}", flush=True)


if __name__ == "__main__":
    main()
