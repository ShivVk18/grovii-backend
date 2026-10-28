import logging
import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
# A worker runs one job at a time; it needs few DB connections. Set before the
# database engine is created. Override with DB_POOL_SIZE / DB_MAX_OVERFLOW.
os.environ.setdefault("DB_POOL_SIZE", "2")
os.environ.setdefault("DB_MAX_OVERFLOW", "1")

from rq import SimpleWorker  # noqa: E402

from src.config.logging_config import setup_logging  # noqa: E402
from src.config.observability import init_sentry  # noqa: E402
from src.services.queue_service import storyboard_queue  # noqa: E402
from src.services.redis_service import redis_client  # noqa: E402

setup_logging()       # JSON lines in production, with job and request ids
init_sentry("worker")  # off unless SENTRY_DSN is set
logger = logging.getLogger("grovii.worker")

# Same Queue object (and name) the API enqueues to: src/config/jobs.py.
QUEUES = [storyboard_queue]

worker = SimpleWorker(QUEUES, connection=redis_client)

if __name__ == "__main__":
    from src.services.reaper import start_background_reaper

    logger.info("Worker started; listening on %s", [q.name for q in QUEUES])
    start_background_reaper()
    worker.work(with_scheduler=True, logging_level=os.getenv("LOG_LEVEL", "INFO"))
