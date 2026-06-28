import uuid

from sqlalchemy import Column, String, Integer,  ForeignKey


from src.database import Base
 
 
class MusicSuggestion(Base):



    __tablename__="music"



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



    genre=Column(String)



    bpm=Column(Integer)



    mood=Column(String)



    transition=Column(String)