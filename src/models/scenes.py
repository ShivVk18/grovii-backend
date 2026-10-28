import uuid

from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime,JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB
from src.database import Base


class Scene(Base):

    __tablename__="scenes"



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



    title=Column(String)



    duration=Column(String)



    camera_angle=Column(String)



    camera_movement=Column(String)



    lighting=Column(String)



    transition=Column(String)



    music_mood=Column(String)



    subject=Column(String)



    broll=Column(Text)



    dos=Column(JSON)



    donts=Column(JSON)



    script_segment=Column(Text)

    scene_prompt=Column(Text)

    what_to_show=Column(Text)

    voiceover_example=Column(Text)

    onscreen_text=Column(String)

    what_to_record=Column(Text)

    what_to_say=Column(Text)

    tips=Column(Text)

    emotion=Column(String)

    advanced=Column(JSONB)  # JSONB in the database (matches migration d3c4e5f6a7b8)

    negative_prompt=Column(Text)



    storyboard=relationship(

        "Storyboard",

        back_populates="scenes"

    )
