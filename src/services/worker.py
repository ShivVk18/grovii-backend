import logging
import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
# A worker runs one job at a time; it needs few DB connections. Set before the
# database engine is created. Override with DB_POOL_SIZE / DB_MAX_OVERFLOW.
os.environ.setdefault("DB_POOL_SIZE", "2")
os.environ.setdefault("DB_MAX_OVERFLOW", "1")

from rq import SimpleWorker  # noqa: E402

from src.services.queue_service import storyboard_queue  # noqa: E402
from src.services.redis_service import redis_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
from src.config.log_safety import install_redaction  # noqa: E402

install_redaction()
logger = logging.getLogger("grovii.worker")

# Same Queue object (and name) the API enqueues to: src/config/jobs.py.
QUEUES = [storyboard_queue]

worker = SimpleWorker(QUEUES, connection=redis_client)

if __name__ == "__main__":
    from src.services.reaper import start_background_reaper

    logger.info("Worker started; listening on %s", [q.name for q in QUEUES])
    start_background_reaper()
    worker.work(with_scheduler=True, logging_level="INFO")
