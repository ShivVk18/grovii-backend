import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"]="YES"

from rq import Worker

from src.services.redis_service import redis_client
from src.services.queue_service import storyboard_queue



worker = Worker(

        [storyboard_queue],

        connection=redis_client

)



if __name__=="__main__":


    print(

        "Starting Grovii Worker..."

    )


    worker.work(
        with_scheduler=True,

    logging_level="INFO"
    )