import os

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Import all models so they're registered with Base.metadata
import src.models  # noqa: F401
from src.api.auth import router as auth_router
from src.api.errors import register_error_handlers
from src.api.middleware import SecurityMiddleware
from src.api.storyboard import router as storyboard_router
from src.config import security_settings
from src.config.log_safety import install_redaction
from src.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (will fail gracefully if DB is unreachable)
    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE storyboards ADD COLUMN IF NOT EXISTS language VARCHAR DEFAULT 'English'"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS what_to_show TEXT"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS voiceover_example TEXT"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS onscreen_text VARCHAR"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS what_to_record TEXT"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS what_to_say TEXT"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS tips TEXT"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS emotion VARCHAR"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS advanced JSONB"))
            conn.execute(text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS scene_prompt TEXT"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS song_name VARCHAR"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS artist VARCHAR"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS why_fits TEXT"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS best_scene VARCHAR"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS platform_popularity VARCHAR"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS royalty_free_alt VARCHAR"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS trending_instagram JSONB"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS trending_tiktok JSONB"))
            conn.execute(text("ALTER TABLE music ADD COLUMN IF NOT EXISTS trending_youtube JSONB"))
            conn.commit()
        print("✅ Database tables created/migrated")
    except Exception as e:
        print(f"⚠️  Could not create/migrate tables (DB might be unavailable): {e}")
    yield


app = FastAPI(title="Grovii Backend", lifespan=lifespan)
register_error_handlers(app)
install_redaction()

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


app.include_router(auth_router)
app.include_router(storyboard_router)


@app.get("/")
def root():
    return {"message": "Welcome to Grovii API!"}


@app.get("/health")
def health():
    return {"status": "ok"}
