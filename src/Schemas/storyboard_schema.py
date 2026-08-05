from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class CreateStoryboardRequest(BaseModel):
    idea: str
    goal: str
    tone: str
    style: str
    audience: str
    duration: int
    platform: str
    language: Optional[str] = "English"


class UpdateStoryboardRequest(BaseModel):
    title: Optional[str] = None
    idea: Optional[str] = None
    goal: Optional[str] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    audience: Optional[str] = None
    duration: Optional[int] = None
    platform: Optional[str] = None
    language: Optional[str] = None


class StoryboardResponse(BaseModel):

    id: UUID

    title: Optional[str]

    idea: str

    goal: str

    tone: str

    style: str

    audience: str

    duration: int

    platform: str
    
    language: Optional[str] = "English"
    
    thumbnail_url: Optional[str] = None
    
    thumbnail_status: Optional[str] = "pending"
    
    thumbnail_prompt: Optional[str] = None

    created_at: datetime


    class Config:
        from_attributes = True


class AdvancedSceneDetails(BaseModel):
    camera_angle: Optional[str] = None
    camera_movement: Optional[str] = None
    lighting: Optional[str] = None
    transition: Optional[str] = None
    music: Optional[str] = None
    scene_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    reference_prompt: Optional[str] = None
    image_generation_prompt: Optional[str] = None
    director_notes: Optional[str] = None
    technical_settings: Optional[str] = None

    class Config:
        from_attributes = True


class SceneResponse(BaseModel):
    id: UUID
    scene_number: int
    title: Optional[str] = None
    duration: Optional[str] = None
    what_to_show: Optional[str] = None
    voiceover_example: Optional[str] = None
    onscreen_text: Optional[str] = None
    what_to_record: Optional[str] = None
    what_to_say: Optional[str] = None
    tips: Optional[str] = None
    emotion: Optional[str] = None
    advanced: Optional[dict] = None

    # Legacy fields kept for backward compatibility
    camera_angle: Optional[str] = None
    camera_movement: Optional[str] = None
    lighting: Optional[str] = None
    transition: Optional[str] = None
    music_mood: Optional[str] = None
    subject: Optional[str] = None
    broll: Optional[str] = None
    dos: Optional[list] = None
    donts: Optional[list] = None
    script_segment: Optional[str] = None
    scene_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    
    class Config:
        from_attributes = True


class CaptionResponse(BaseModel):
    id: UUID
    caption: str
    class Config:
        from_attributes = True


class HashtagResponse(BaseModel):
    id: UUID
    hashtag: str
    class Config:
        from_attributes = True


class HookResponse(BaseModel):
    id: UUID
    hook: str
    selected: bool
    class Config:
        from_attributes = True


class MusicResponse(BaseModel):
    id: UUID
    song_name: Optional[str] = None
    artist: Optional[str] = None
    why_fits: Optional[str] = None
    best_scene: Optional[str] = None
    mood: Optional[str] = None
    platform_popularity: Optional[str] = None
    royalty_free_alt: Optional[str] = None
    trending_instagram: Optional[list] = None
    trending_tiktok: Optional[list] = None
    trending_youtube: Optional[list] = None
    genre: Optional[str] = None
    class Config:
        from_attributes = True


class TrendResponse(BaseModel):
    id: UUID
    posting_time: Optional[str] = None
    editing_style: Optional[str] = None
    content_gap: Optional[str] = None
    transitions: Optional[list] = None
    sounds: Optional[list] = None
    class Config:
        from_attributes = True


class RepurposeResponse(BaseModel):
    id: UUID
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    carousel: Optional[str] = None
    blog: Optional[str] = None
    newsletter: Optional[str] = None
    class Config:
        from_attributes = True


class StoryboardDetailResponse(StoryboardResponse):
    hook: Optional[str] = None
    script: Optional[str] = None
    status: str
    scenes: list[SceneResponse] = []
    captions: list[CaptionResponse] = []
    hashtags: list[HashtagResponse] = []
    hooks: list[HookResponse] = []
    music: list[MusicResponse] = []
    trends: list[TrendResponse] = []
    repurpose: Optional[RepurposeResponse] = None