from rq import Queue

from src.config.jobs import STORYBOARD_QUEUE_NAME
from src.services.redis_service import redis_client

storyboard_queue = Queue(name=STORYBOARD_QUEUE_NAME, connection=redis_client)
