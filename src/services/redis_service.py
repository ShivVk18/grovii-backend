import os

from dotenv import load_dotenv
from redis import Redis

load_dotenv()

# Default matches the old hardcoded value (localhost:6379, db 0).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = Redis.from_url(REDIS_URL)
