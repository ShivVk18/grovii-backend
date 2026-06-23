from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    username = Column(
        String,
        unique=True
    )

    email = Column(
        String,
        unique=True
    )

    hashed_password = Column(
        String
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    storyboards = relationship(
        "Storyboard",
        back_populates="user"
    )