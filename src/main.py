import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models so they're registered with Base.metadata
import src.models  # noqa: F401
from src.api.auth import router as auth_router
from src.api.errors import register_error_handlers
from src.api.middleware import RequestContextMiddleware, SecurityMiddleware
from src.api.ops import router as ops_router
from src.api.storyboard import router as storyboard_router
from src.config import security_settings
from src.config.logging_config import setup_logging
from src.config.observability import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The schema is managed only by Alembic, run as a deploy step
    # (`alembic upgrade head`); the app never creates or alters tables.
    # /ready reports 503 until the database is at the code's migration head.
    yield


app = FastAPI(title="Grovii Backend", lifespan=lifespan)
register_error_handlers(app)
setup_logging()
init_sentry("api")

# Explicit origins only (CORS_ORIGINS env). In production the browser calls the
# frontend's own domain and Next.js proxies to this API, so CORS mostly matters
# in local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", security_settings.CSRF_HEADER],
    max_age=600,
)
# Added last = runs first: size limit, Origin check, security headers.
app.add_middleware(SecurityMiddleware)
# Outermost: request id + latency cover everything, including 413/403 above.
app.add_middleware(RequestContextMiddleware)


app.include_router(ops_router)
app.include_router(auth_router)
app.include_router(storyboard_router)


@app.get("/")
def root():
    return {"message": "Welcome to Grovii API!"}

