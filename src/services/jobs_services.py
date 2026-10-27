import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

import logging

from src.database import SessionLocal
from src.repositories.job_repository import (
    get_job,
    mark_completed,
    mark_failed,
    mark_processing,
    update_progress,
)
from src.repositories.storyboard_repository import save_graph_result
from src.services.credits_service import is_user_fault, refund_job_credits
from src.services.llm_usage import BudgetExceeded, metered
from src.services.spend_service import record_job_usage

logger = logging.getLogger("grovii.jobs_services")


def generate_storyboard_job(
        payload,
        storyboard_id,
        job_id
):
    db = SessionLocal()
    # Every LLM call made while this job runs is counted against its token budget.
    usage_scope = metered()
    meter = usage_scope.__enter__()

    try:
        ################################################
        # Fetch Job
        ################################################
        logger.info(f"Stage: Fetching Job {job_id}")
        job = get_job(
            db,
            job_id
        )

        if not job:
            raise Exception(
                "Job not found"
            )
        logger.info("Stage: Job Loaded")

        ################################################
        # Processing
        ################################################
        logger.info("Stage: Processing Started")
        mark_processing(
            db,
            job
        )

        ################################################
        # LangGraph
        ################################################
        logger.info("Stage: Graph Started")
        from src.ai.graph import graph

        progress_map = {
            "hook": 15,
            "hook_regenerator": 25,
            "director": 45,
            "script": 60,
            "caption": 70,
            "hashtag": 75,
            "music": 80,
            "trend": 85,
            "repurpose": 90,
            "collector": 95,
        }

        final_state = dict(payload)
        for update in graph.stream(payload, stream_mode="updates"):
            for node_name, node_output in update.items():
                if isinstance(node_output, dict):
                    final_state.update(node_output)
                if node_name in progress_map:
                    try:
                        job = get_job(db, job_id)
                        if job:
                            update_progress(db, job, progress_map[node_name])
                    except Exception as pe:
                        logger.warning(f"Could not update progress for {node_name}: {pe}")

        # Nodes catch their own errors, so a refused call shows up only on the meter.
        if meter.exceeded:
            raise BudgetExceeded(
                f"Generation stopped: the job reached its token budget ({meter.budget} tokens)."
            )

        ################################################
        # Persist
        ################################################
        logger.info("Stage: Saving Results")
        save_graph_result(
            db,
            storyboard_id,
            final_state
        )

        ################################################
        # Complete
        ################################################
        logger.info("Stage: Completed")
        job = get_job(db, job_id)
        if job:
            mark_completed(
                db,
                job
            )

        return final_state

    except Exception as e:
        logger.error(f"Stage: Failed - Job {job_id} failed: {e}")
        try:
            job = get_job(db, job_id)
            if job:
                mark_failed(
                    db,
                    job,
                    str(e)
                )
        except Exception:
            pass
        # Give the credit back unless the provider refused the user's own input.
        try:
            if not is_user_fault(e):
                refund_job_credits(db, job_id)
        except Exception as refund_error:
            logger.error(f"Refund failed for job {job_id}: {refund_error}")
        raise e
    finally:
        usage_scope.__exit__(None, None, None)
        # Record what this job spent, whether it succeeded or failed.
        try:
            record_job_usage(db, job_id, meter)
        except Exception as usage_error:
            logger.error(f"Could not record LLM usage for job {job_id}: {usage_error}")
        db.close()

