import uuid

from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base


class Scene(Base):

    __tablename__ = "scenes"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    storyboard_id = Column(
        String,
        ForeignKey("storyboards.id")
    )

    order = Column(Integer)
    title = Column(String)
    description = Column(Text)
    visual_cue = Column(Text)
    script_segment = Column(Text)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    storyboard = relationship(
        "Storyboard",
        back_populates="scenes"
    )