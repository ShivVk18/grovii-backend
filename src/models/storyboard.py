import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database import Base


class Storyboard(Base):

    __tablename__="storyboards"

    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )

    user_id=Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE")
    )

    title=Column(String)

    idea=Column(Text)

    goal=Column(String)

    tone=Column(String)

    style=Column(String)

    audience=Column(String)

    duration=Column(Integer)

    platform=Column(String)

    language=Column(String, default="English")

    # draft/created (no generation), queued, running, completed, partial,
    # failed, cancelled. Generation statuses mirror the job (see job_lifecycle).
    status=Column(
        String,
        default="draft"
    )

    # Plain-language explanation shown to the creator for partial/failed
    # storyboards (never internal error text).
    status_reason=Column(Text, nullable=True)

    # Creator constraints (faceless/location/equipment) and, for open briefs,
    # the concrete example the planner chose (Phase D).
    constraints=Column(JSONB, nullable=True)
    brief_choice=Column(Text, nullable=True)



    hook=Column(Text)

    script=Column(Text)



    thumbnail_prompt=Column(Text)

    thumbnail_url=Column(String)



    total_tokens=Column(
        Integer,
        default=0
    )


    total_cost=Column(
        Float,
        default=0
    )


    latency=Column(
        Float,
        default=0
    )



    created_at=Column(
        DateTime,
        default=datetime.utcnow
    )


    updated_at=Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    user=relationship(
        "User",
        back_populates="storyboards"
    )


    scenes=relationship(
        "Scene",
        cascade="all, delete-orphan",
        back_populates="storyboard"
    )


    captions=relationship(
        "Caption",
        cascade="all, delete-orphan"
    )



    hashtags=relationship(
        "Hashtag",
        cascade="all, delete-orphan"
    )


    hooks=relationship(
        "Hook",
        cascade="all, delete-orphan"
    )


    trends=relationship(
        "Trend",
        cascade="all, delete-orphan"
    )


    music=relationship(
        "MusicSuggestion",
        cascade="all, delete-orphan"
    )



    repurpose=relationship(
        "RepurposeContent",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    jobs = relationship(

        "Job",

        cascade="all,delete"

)
