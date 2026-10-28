from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.ai.prompt_safety import neutralize_delimiters
from src.Schemas.options import GOALS, LANGUAGES, PLATFORMS, STYLES, TONES, canonical

IDEA_MIN, IDEA_MAX = 10, 1000
AUDIENCE_MIN, AUDIENCE_MAX = 2, 200
TITLE_MIN, TITLE_MAX = 1, 200
DURATION_MIN, DURATION_MAX = 15, 180


def _text(value: Any, label: str, lo: int, hi: int) -> str:
    """Trim whitespace and enforce a length range, with a message the UI can show."""
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = neutralize_delimiters(value.strip())
    if len(value) < lo:
        raise ValueError(f"{label} must be at least {lo} characters.")
    if len(value) > hi:
        raise ValueError(f"{label} must be at most {hi} characters.")
    return value


def _duration(value: Any) -> int:
    message = f"Duration must be between {DURATION_MIN} and {DURATION_MAX} seconds."
    if isinstance(value, bool):
        raise ValueError(message)
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if not isinstance(value, int) or not DURATION_MIN <= value <= DURATION_MAX:
        raise ValueError(message)
    return value


class _StoryboardFields(BaseModel):
    """Validators shared by create and update. A None value means "not given"."""

    @field_validator("idea", mode="before", check_fields=False)
    @classmethod
    def _idea(cls, v):
        return None if v is None else _text(v, "Idea", IDEA_MIN, IDEA_MAX)

    @field_validator("audience", mode="before", check_fields=False)
    @classmethod
    def _audience(cls, v):
        return None if v is None else _text(v, "Audience", AUDIENCE_MIN, AUDIENCE_MAX)

    @field_validator("duration", mode="before", check_fields=False)
    @classmethod
    def _dur(cls, v):
        return None if v is None else _duration(v)

    @field_validator("platform", mode="before", check_fields=False)
    @classmethod
    def _platform(cls, v):
        return None if v is None else canonical(PLATFORMS, v, "Platform")

    @field_validator("goal", mode="before", check_fields=False)
    @classmethod
    def _goal(cls, v):
        return None if v is None else canonical(GOALS, v, "Goal")

    @field_validator("tone", mode="before", check_fields=False)
    @classmethod
    def _tone(cls, v):
        return None if v is None else canonical(TONES, v, "Tone")

    @field_validator("style", mode="before", check_fields=False)
    @classmethod
    def _style(cls, v):
        return None if v is None else canonical(STYLES, v, "Style")

    @field_validator("language", mode="before", check_fields=False)
    @classmethod
    def _language(cls, v):
        return None if v is None else canonical(LANGUAGES, v, "Language")


CONSTRAINT_MAX = 120


def _optional_text(v, label):
    if v is None:
        return None
    text = _text(v, label, 0, CONSTRAINT_MAX)
    return text or None


class CreateStoryboardRequest(_StoryboardFields):
    idea: str
    goal: str
    tone: str
    style: str
    audience: str
    duration: int
    platform: str
    language: str = "English"
    # Optional creator constraints (Phase D): respected by the scene planner.
    faceless: bool = False
    location: Optional[str] = None
    equipment: Optional[str] = None

    @field_validator("location", mode="before")
    @classmethod
    def _location(cls, v):
        return _optional_text(v, "Location")

    @field_validator("equipment", mode="before")
    @classmethod
    def _equipment(cls, v):
        return _optional_text(v, "Equipment")

    def constraints(self) -> dict:
        return {"faceless": self.faceless, "location": self.location, "equipment": self.equipment}

    @field_validator("language", mode="before")
    @classmethod
    def _language_default(cls, v):
        return "English" if v is None else v


class UpdateStoryboardRequest(_StoryboardFields):
    title: Optional[str] = None
    idea: Optional[str] = None
    goal: Optional[str] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    audience: Optional[str] = None
    duration: Optional[int] = None
    platform: Optional[str] = None
    language: Optional[str] = None

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, v):
        return None if v is None else _text(v, "Title", TITLE_MIN, TITLE_MAX)


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

    # Phase D
    constraints: Optional[dict] = None
    brief_choice: Optional[str] = None

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
    start_seconds: Optional[int] = None
    end_seconds: Optional[int] = None
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
    verified: Optional[bool] = None
    licensing_note: Optional[str] = None
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
    status_reason: Optional[str] = None
    scenes: list[SceneResponse] = []
    captions: list[CaptionResponse] = []
    hashtags: list[HashtagResponse] = []
    hooks: list[HookResponse] = []
    music: list[MusicResponse] = []
    trends: list[TrendResponse] = []
    repurpose: Optional[RepurposeResponse] = None