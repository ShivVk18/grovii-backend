from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.database import Base, engine

# Import all models so they're registered with Base.metadata
import src.models  # noqa: F401

from src.api.auth import router as auth_router
from src.api.storyboard import router as storyboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (will fail gracefully if DB is unreachable)
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️  Could not create tables (DB might be unavailable): {e}")
    yield


app = FastAPI(title="Grovii Backend", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(storyboard_router)


@app.get("/")
def root():
    return {"message": "Welcome to Grovii API!"}
