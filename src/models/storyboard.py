import uuid

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey,Float
from sqlalchemy.orm import relationship
from datetime import datetime


from src.database import Base


class Storyboard(Base):

    __tablename__="storyboards"

    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )

    user_id=Column(
        String,
        ForeignKey("users.id")
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

    status=Column(
        String,
        default="draft"
    )



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
        back_populates="storyboard"
    )


    captions=relationship(
        "Caption"
    )



    hashtags=relationship(
        "Hashtag"
    )


    hooks=relationship(
        "Hook"
    )


    trends=relationship(
        "Trend"
    )


    music=relationship(
        "MusicSuggestion"
    )



    repurpose=relationship(
        "RepurposeContent",
        uselist=False
    )
    
    jobs = relationship(

        "Job",

        cascade="all,delete"

)
