import os
import logging

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

from rq import Worker

from src.services.redis_service import redis_client
from src.services.queue_service import storyboard_queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("grovii.worker")

worker = Worker(
    [storyboard_queue],
    connection=redis_client
)

if __name__ == "__main__":
    logger.info("Stage: Worker Started")
    worker.work(
        with_scheduler=True,
        logging_level="INFO"
    )