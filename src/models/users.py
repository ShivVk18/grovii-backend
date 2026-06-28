import uuid

from sqlalchemy import *
from sqlalchemy.orm import relationship

from src.database import Base
from datetime import datetime  

class User(Base):
    __tablename__ = "users"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    username = Column(
        String,
        unique=True,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    hashed_password = Column(
        String,
        nullable=False
    )

    avatar_url = Column(String)

    plan = Column(
        String,
        default="free"
    )

    credits = Column(
        Integer,
        default=100
    )

    is_verified = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    storyboards = relationship(
        "Storyboard",
        back_populates="user",
        cascade="all,delete"
    )
    
    jobs = relationship(

        "Job",

        cascade="all,delete"

)