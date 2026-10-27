from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator


class GraphState(BaseModel):

    # User Input
    idea:str
    goal:str

    tone:str

    style:str

    audience:str

    duration:int = 30

    @field_validator("duration", mode="before")
    @classmethod
    def parse_duration(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            import re
            digits = re.findall(r"\d+", v)
            if digits:
                return int(digits[0])
        return 30

    platform:str
    language:str="English"


    #################################
    # Hook
    #################################

    hook:str=""


    regenerated_hooks:List[dict]=Field(
        default_factory=list
    )


    hook_error:Optional[str]=None



    #################################
    # Director
    #################################

    scenes:List[dict]=Field(

        default_factory=list
    )



    scene_error:Optional[str]=None



    #################################
    # Script
    #################################

    script:str=""


    script_error:Optional[str]=None




    #################################
    # Captions
    #################################

    captions:List[dict]=Field(

        default_factory=list
    )



    caption_error:Optional[str]=None




    #################################
    # Hashtags
    #################################

    hashtags:List[dict]=Field(

        default_factory=list
    )



    hashtag_error:Optional[str]=None




    #################################
    # Trend
    #################################


    trends:Dict={}


    trend_error:Optional[str]=None




    #################################
    # Music
    #################################


    scene_music:List[dict]=Field(

        default_factory=list
    )



    music_error:Optional[str]=None




    #################################
    # Repurpose
    #################################


    repurposed_content:Dict={}



    repurpose_error:Optional[str]=None




    #################################
    # Thumbnail
    #################################


    thumbnail_prompt:str=""


    thumbnail_url:str=""




    #################################
    # Metrics
    #################################


    total_tokens:int=0


    total_cost:float=0


    latency:float=0




    #################################
    # Debug
    #################################


    errors:List[str]=Field(

        default_factory=list
    )




    #################################
    # Status
    #################################


    status:str="pending"



