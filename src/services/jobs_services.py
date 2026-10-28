import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

import logging

from rq import get_current_job

from src.database import SessionLocal
from src.models.jobs import Job, JobStatus
from src.repositories.job_repository import get_job, update_progress
from src.repositories.storyboard_repository import save_graph_result
from src.ai.quality import language_problems
from src.services.credits_service import is_user_fault
from src.services.job_lifecycle import USER_MESSAGES, transition
from src.services.llm_usage import BudgetExceeded, metered
from src.services.spend_service import record_job_usage

logger = logging.getLogger("grovii.jobs_services")

PROGRESS = {
    "hook": 15, "director": 45, "script": 60, "caption": 70,
    "hashtag": 75, "music": 80, "trend": 85, "repurpose": 90, "collector": 95,
}
# Outputs a creator can live without; missing ones are reported, not fatal.
OPTIONAL_PARTS = {
    "captions": "captions", "hashtags": "hashtags", "scene_music": "music suggestions",
    "trends": "posting tips", "repurposed_content": "repurposed posts",
}


class CriticalOutputMissing(RuntimeError):
    """A node the storyboard cannot work without produced nothing."""


def _retries_left() -> int:
    """Retries RQ still has for this job after the current attempt (0 outside RQ)."""
    rq_job = get_current_job()
    return int(getattr(rq_job, "retries_left", 0) or 0) if rq_job is not None else 0


def _language_texts(state: dict) -> dict[str, str]:
    scenes = state.get("scenes") or []
    return {
        "hook": state.get("hook") or "",
        "script": state.get("script") or "",
        "scene directions": " ".join(str(s.get("what_to_show") or "") for s in scenes),
        "on-screen text": " ".join(str(s.get("onscreen_text") or "") for s in scenes),
        "captions": " ".join(str(c.get("caption") if isinstance(c, dict) else c) for c in state.get("captions") or []),
        "repurposed posts": str((state.get("repurposed_content") or {}).get("linkedin") or ""),
    }


def _missing_optional(state: dict) -> list[str]:
    return [label for key, label in OPTIONAL_PARTS.items() if not state.get(key)]


def generate_storyboard_job(payload, storyboard_id, job_id):
    """Run one generation attempt. Safe to call more than once for the same job:
    finished jobs are skipped and saving replaces earlier partial writes."""
    db = SessionLocal()
    usage_scope = metered()
    meter = usage_scope.__enter__()
    try:
        job = get_job(db, job_id)
        if job is None:
            logger.error("Job %s not found; nothing to do", job_id)
            return None
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            logger.info("Job %s already %s; skipping re-delivery", job_id, job.status.value)
            return None

        transition(db, job_id, JobStatus.RUNNING)

        from src.ai.graph import graph

        final_state = dict(payload)
        for update in graph.stream(payload, stream_mode="updates"):
            for node_name, node_output in update.items():
                if isinstance(node_output, dict):
                    final_state.update(node_output)
                if node_name in PROGRESS:
                    try:
                        job = get_job(db, job_id)
                        if job:
                            update_progress(db, job, PROGRESS[node_name])
                    except Exception as pe:  # noqa: BLE001 - progress is best effort
                        logger.warning("Could not update progress for %s: %s", node_name, pe)

        # Nodes catch their own errors, so a refused call shows up only on the meter.
        if meter.exceeded:
            raise BudgetExceeded(f"Job reached its token budget ({meter.budget} tokens).")
        # Fail closed: without scenes there is nothing to shoot (RES-02).
        if not final_state.get("scenes"):
            raise CriticalOutputMissing(f"scene node produced no scenes: {final_state.get('scene_error')}")

        save_graph_result(db, storyboard_id, final_state)

        if not (final_state.get("script") or "").strip():
            transition(db, job_id, JobStatus.COMPLETED, storyboard_status="partial",
                       reason=USER_MESSAGES["script_missing"],
                       internal_error=f"script missing: {final_state.get('script_error')}", refund=True)
        else:
            notes = []
            missing = _missing_optional(final_state)
            if missing:
                notes.append(f"Your storyboard is ready, but these extras couldn't be generated: {', '.join(missing)}.")
            # Final language check (QUAL-03): flag parts that don't look like the requested language.
            language = final_state.get("language") or "English"
            off = language_problems(language, _language_texts(final_state))
            if off:
                logger.warning("Job %s language check failed for %s: %s", job_id, language, off)
                notes.append(f"Some parts may not be fully in {language}: {', '.join(off)}. Please review them.")
            transition(db, job_id, JobStatus.COMPLETED, storyboard_status="completed",
                       reason=" ".join(notes) or None)
        return final_state

    except BudgetExceeded as e:
        # Not retried: a retry would hit the same budget.
        logger.error("Job %s stopped: %s", job_id, e)
        transition(db, job_id, JobStatus.FAILED, reason=USER_MESSAGES["budget"],
                   internal_error=f"token budget: {e}", refund=True)
        return None
    except Exception as e:  # noqa: BLE001 - every failure must end in a clear state
        kind = type(e).__name__
        if is_user_fault(e):
            logger.warning("Job %s refused by provider (user content): %s", job_id, e)
            transition(db, job_id, JobStatus.FAILED, reason=USER_MESSAGES["user_fault"],
                       internal_error=f"{kind}: {e}", refund=False)
            return None
        if _retries_left() > 0:
            logger.warning("Job %s attempt failed (%s: %s); RQ will retry", job_id, kind, e)
            transition(db, job_id, JobStatus.QUEUED, internal_error=f"retrying after {kind}: {e}")
            raise
        key = "scenes_missing" if isinstance(e, CriticalOutputMissing) else (
            "timeout" if "timeout" in kind.lower() else "failed")
        logger.error("Job %s failed on its last attempt (%s: %s)", job_id, kind, e)
        transition(db, job_id, JobStatus.FAILED, reason=USER_MESSAGES[key],
                   internal_error=f"{kind}: {e}", refund=True)
        if isinstance(e, CriticalOutputMissing):
            return None
        raise
    finally:
        usage_scope.__exit__(None, None, None)
        try:
            record_job_usage(db, job_id, meter)
        except Exception as usage_error:  # noqa: BLE001
            logger.error("Could not record LLM usage for job %s: %s", job_id, usage_error)
        db.close()


__all__ = ["generate_storyboard_job", "Job"]
