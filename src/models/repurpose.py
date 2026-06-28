import uuid

from sqlalchemy import Column, String,  ForeignKey,Text


from src.database import Base 

class RepurposeContent(Base):


    __tablename__="repurpose"



    id=Column(String,
        primary_key=True,
        default=lambda:str(uuid.uuid4())
    )



    storyboard_id=Column(

        String,

        ForeignKey(

            "storyboards.id"

        ),

        unique=True

    )



    linkedin=Column(Text)



    twitter=Column(Text)



    carousel=Column(Text)



    blog=Column(Text)



    newsletter=Column(Text)
