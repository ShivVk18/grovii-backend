import os
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.database import Base, engine

# Import all models so they're registered with Base.metadata
import src.models  # noqa: F401

from src.api.auth import router as auth_router
from src.api.storyboard import router as storyboard_router


from sqlalchemy import text


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
print("Adding CORS middleware...")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(storyboard_router)


@app.get("/")
def root():
    return {"message": "Welcome to Grovii API!"}
