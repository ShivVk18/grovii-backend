import uuid

from sqlalchemy import Column, String,  Integer, ForeignKey


from src.database import Base


class Hashtag(Base):


    __tablename__="hashtags"



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



    hashtag=Column(String)



    hashtag_type=Column(String)



    score=Column(Integer)
