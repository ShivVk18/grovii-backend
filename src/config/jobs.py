"""Background job settings: queue name, timeouts, retries, reaper.
Every value can be overridden with an environment variable of the same name."""
import os

from dotenv import load_dotenv

load_dotenv()

# The ONE place the queue name is defined. The API enqueues to it, the worker
# listens on it, health checks inspect it. (Bug OPS-01 came from two spellings.)
STORYBOARD_QUEUE_NAME = os.getenv("STORYBOARD_QUEUE_NAME", "storyboards")

# Local development only: run jobs inside the API process when no worker is
# running. Never enable in production: it ties LLM work to web threads.
ALLOW_INPROCESS_JOBS = os.getenv("ALLOW_INPROCESS_JOBS", "false").strip().lower() in ("1", "true", "yes")

# Hard limit for one attempt of a generation job (RQ kills it after this).
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "300"))
# Extra attempts after a failure (so at most 1 + JOB_MAX_RETRIES runs).
JOB_MAX_RETRIES = int(os.getenv("JOB_MAX_RETRIES", "2"))
JOB_RETRY_INTERVALS = [15, 60]  # seconds to wait before retry 1, retry 2

# Reaper: a job still queued after this long (no worker picked it up) fails.
QUEUED_TIMEOUT_MINUTES = int(os.getenv("QUEUED_TIMEOUT_MINUTES", "30"))
# A running job is stuck if it started longer ago than all attempts could take.
RUNNING_TIMEOUT_MINUTES = int(os.getenv(
    "RUNNING_TIMEOUT_MINUTES",
    str((JOB_TIMEOUT_SECONDS * (1 + JOB_MAX_RETRIES) + sum(JOB_RETRY_INTERVALS)) // 60 + 5),
))
REAPER_INTERVAL_SECONDS = int(os.getenv("REAPER_INTERVAL_SECONDS", "60"))
