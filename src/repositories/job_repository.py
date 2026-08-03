from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.models.jobs import Job, JobStatus


def create_job(
        db: Session,
        job: Job
) -> Job:
    try:

        db.add(job)

        db.commit()

        db.refresh(job)

        return job

    except Exception as e:

        db.rollback()

        raise e


def get_job(
        db: Session,
        job_id: str
):
    return (

        db.query(Job)

        .filter(

            Job.id == job_id

        )

        .first()

    )


def get_queue_job(
        db: Session,
        queue_job_id: str
):
    return (

        db.query(Job)

        .filter(

            Job.queue_job_id == queue_job_id

        )

        .first()

    )


def update_progress(

        db: Session,

        job: Job,

        progress: int

):
    try:


        job.progress = progress


        db.commit()


        db.refresh(job)


        return job


    except Exception as e:


        db.rollback()


        raise e


def mark_processing(

        db: Session,

        job: Job

):
    try:


        job.status = JobStatus.PROCESSING


        job.started_at = datetime.now(timezone.utc)


        db.commit()


        db.refresh(job)


        return job


    except Exception as e:


        db.rollback()


        raise e



def mark_completed(

        db: Session,

        job: Job

):
    try:


        job.status = JobStatus.COMPLETED


        job.progress = 100


        job.completed_at = datetime.now(timezone.utc)


        db.commit()


        db.refresh(job)


        return job


    except Exception as e:


        db.rollback()


        raise e



def mark_failed(

        db: Session,

        job: Job,

        error_message: str

):
    try:


        job.status = JobStatus.FAILED


        job.error_message = error_message


        job.completed_at = datetime.now(timezone.utc)


        db.commit()


        db.refresh(job)


        return job


    except Exception as e:


        db.rollback()


        raise e



def update_queue_job_id(

        db: Session,

        job: Job,

        queue_job_id: str

):
    try:


        job.queue_job_id = queue_job_id


        db.commit()


        db.refresh(job)


        return job


    except Exception as e:


        db.rollback()


        raise e



def delete_job(

        db: Session,

        job: Job

):
    try:


        db.delete(job)


        db.commit()


        return True


    except Exception as e:


        db.rollback()


        raise e