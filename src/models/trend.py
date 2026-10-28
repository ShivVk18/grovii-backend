import uuid

from sqlalchemy import JSON, Column, ForeignKey, String, Text

from src.database import Base


class Trend(Base):


    __tablename__="trends"



    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )



    storyboard_id=Column(

        String,

        ForeignKey("storyboards.id", ondelete="CASCADE")

    )



    posting_time=Column(String)



    editing_style=Column(String)



    content_gap=Column(Text)



    transitions=Column(JSON)



    sounds=Column(JSON)
