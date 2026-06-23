import uuid

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base


class Storyboard(Base):

    __tablename__ = "storyboards"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    title = Column(String)
    idea = Column(Text)
    goal = Column(String)
    tone = Column(String)
    style = Column(String)
    audience = Column(String)
    duration = Column(Integer)
    platform = Column(String)

    status = Column(
        String,
        default="draft"
    )

    script = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="storyboards"
    )

    scenes = relationship(
        "Scene",
        back_populates="storyboard",
        cascade="all,delete"
    )