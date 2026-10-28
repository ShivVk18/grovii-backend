import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from src.database import Base


class MusicSuggestion(Base):

    __tablename__="music"

    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )

    storyboard_id=Column(
        String,
        ForeignKey(
            "storyboards.id"
        )
    )

    scene_number=Column(Integer)

    song_name=Column(String)

    artist=Column(String)

    why_fits=Column(Text)

    best_scene=Column(String)

    mood=Column(String)

    platform_popularity=Column(String)

    royalty_free_alt=Column(String)

    trending_instagram=Column(JSONB)

    trending_tiktok=Column(JSONB)

    trending_youtube=Column(JSONB)

    genre=Column(String)

    bpm=Column(Integer)

    transition=Column(String)