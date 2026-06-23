from pydantic import BaseModel
from typing import List

class SceneSchema(BaseModel):


    title:str


    description:str


    visual_cue:str


    script_segment:str
    

class ScenesResponse(BaseModel):


    scenes:List[SceneSchema]