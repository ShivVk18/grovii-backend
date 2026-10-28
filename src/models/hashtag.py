import uuid

from sqlalchemy import Column, ForeignKey, Integer, String

from src.database import Base


class Hashtag(Base):


    __tablename__="hashtags"



    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )



    storyboard_id=Column(

        String,

        ForeignKey("storyboards.id", ondelete="CASCADE")

    )



    hashtag=Column(String)



    hashtag_type=Column(String)



    score=Column(Integer)
