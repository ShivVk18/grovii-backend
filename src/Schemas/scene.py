from pydantic import BaseModel
from typing import List, Optional

from pydantic import BaseModel
from typing import List


class Scene(BaseModel):

    scene_number:int

    title:str

    duration:str


    camera_angle:str


    camera_movement:str


    lighting:str


    transition:str


    music_mood:str


    subject:str


    broll:str


    dos:List[str]


    donts:List[str]


    script_segment:str


    scene_prompt:str


    negative_prompt:str




class SceneList(BaseModel):

    scenes:List[Scene]