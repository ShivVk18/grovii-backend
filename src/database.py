import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# Connection pool, sized per process. Budget across the whole deployment:
#
#   api_processes x (DB_POOL_SIZE + DB_MAX_OVERFLOW)
# + worker_processes x (worker pool, default 2 + 1)        <= Postgres max_connections
# + headroom for migrations, psql, backups (~10)
#
# Example with max_connections = 100: 2 API processes x (10 + 10) = 40,
# 4 workers x 3 = 12, headroom 10 -> 62 of 100. Raise the API pool only if
# max_connections allows it. When the pool is exhausted a request waits up to
# DB_POOL_TIMEOUT seconds for a connection instead of failing at once.
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "10"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # drop connections older than 30 min

engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # test each connection before use; survives DB restarts
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


async def get_db():
    # Async on purpose: FastAPI then runs this setup/cleanup on the event loop
    # instead of taking a thread-pool slot, so closing a session (which returns
    # its connection) never waits for a free thread. Route handlers stay sync
    # and run in the thread pool; the session is used by one request at a time.
    # See also get_current_user, which ends its transaction for the same reason.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
