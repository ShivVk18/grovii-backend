from pydantic import BaseModel
from typing import List, Optional, Dict


class AdvancedScene(BaseModel):
    camera_angle: Optional[str] = ""
    camera_movement: Optional[str] = ""
    lighting: Optional[str] = ""
    transition: Optional[str] = ""
    music: Optional[str] = ""
    scene_prompt: Optional[str] = ""
    negative_prompt: Optional[str] = ""
    reference_prompt: Optional[str] = ""
    image_generation_prompt: Optional[str] = ""
    director_notes: Optional[str] = ""
    technical_settings: Optional[str] = ""


class Scene(BaseModel):
    scene_number: int
    title: str
    duration: str
    what_to_show: str
    voiceover_example: str
    onscreen_text: Optional[str] = ""
    tips: Optional[str] = ""
    emotion: Optional[str] = ""
    advanced: Optional[Dict] = None

    # Fallback / alias fields
    what_to_record: Optional[str] = None
    what_to_say: Optional[str] = None

    # Legacy fields
    camera_angle: Optional[str] = None
    camera_movement: Optional[str] = None
    lighting: Optional[str] = None
    transition: Optional[str] = None
    music_mood: Optional[str] = None
    subject: Optional[str] = None
    broll: Optional[str] = None
    dos: Optional[List[str]] = None
    donts: Optional[List[str]] = None
    script_segment: Optional[str] = None
    scene_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None


class SceneList(BaseModel):
    scenes: List[Scene]