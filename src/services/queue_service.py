from rq import Queue 

from src.services.redis_service import redis_client 


storyboard_queue = Queue(
    name='storyboards',
    connection=redis_client
)

