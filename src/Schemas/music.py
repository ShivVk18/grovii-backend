from pydantic import BaseModel, Field
from typing import List

class SceneMusic(BaseModel):
    scene: int = Field(description="The scene number")
    genre: str = Field(description="The genre of the music")
    bpm: int = Field(description="The tempo in BPM")
    mood: str = Field(description="The mood of the music")
    transition: str = Field(description="The transition into this scene's music")

class MusicSuggestionOutput(BaseModel):
    scene_music: List[SceneMusic]
