import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from src.database import Base


class Caption(Base):


    __tablename__="captions"



    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )



    storyboard_id=Column(

        String,

        ForeignKey("storyboards.id", ondelete="CASCADE")

    )



    caption=Column(Text)



    caption_type=Column(String)



    score=Column(Integer)
