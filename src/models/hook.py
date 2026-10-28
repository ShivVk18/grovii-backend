import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from src.database import Base


class Hook(Base):


    __tablename__="hooks"



    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )



    storyboard_id=Column(

        String,

        ForeignKey("storyboards.id", ondelete="CASCADE")

    )



    hook=Column(Text)



    framework=Column(String)



    score=Column(Integer)



    selected=Column(

        Boolean,

        default=False

    )
