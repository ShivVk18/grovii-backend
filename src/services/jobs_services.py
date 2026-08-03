import logging
from src.ai.graph import graph

from src.database import SessionLocal

from src.repositories.storyboard_repository import (
    save_graph_result
)

from src.repositories.job_repository import (
    get_job,
    mark_processing,
    mark_completed,
    mark_failed
)

logger = logging.getLogger("grovii.jobs_services")


def generate_storyboard_job(
        payload,
        storyboard_id,
        job_id
):
    db = SessionLocal()

    try:
        ################################################
        # Fetch Job
        ################################################
        logger.info("Stage: Fetching Job")
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
        state = graph.invoke(
            payload
        )

        ################################################
        # Persist
        ################################################
        logger.info("Stage: Saving Results")
        save_graph_result(
            db,
            storyboard_id,
            state
        )

        ################################################
        # Complete
        ################################################
        logger.info("Stage: Completed")
        mark_completed(
            db,
            job
        )

        return state

    except Exception as e:
        logger.error(f"Stage: Failed - Job {job_id} failed: {e}")
        if 'job' in locals() and job:
            mark_failed(
                db,
                job,
                str(e)
            )
        raise e

    finally:
        db.close()
