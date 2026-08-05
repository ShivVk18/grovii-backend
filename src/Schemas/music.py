from pydantic import BaseModel, Field
from typing import List, Optional


class SongRecommendation(BaseModel):
    song_name: str = Field(description="Actual song name, e.g. Golden Hour, Husn, FE!N")
    artist: str = Field(description="Artist name, e.g. JVKE, Anuv Jain, Travis Scott")
    why_fits: str = Field(description="Why this song fits the video concept and mood")
    best_scene: str = Field(description="Best scene placement, e.g. Scene 1-2 or Hook + Ending")
    mood: str = Field(description="Mood of the song, e.g. Calm / Inspirational")
    platform_popularity: Optional[str] = Field(default="High on Instagram Reels & TikTok", description="Platform popularity info")
    royalty_free_alt: Optional[str] = Field(default="", description="Royalty free alternative song if copyrighted")


class MusicSuggestionOutput(BaseModel):
    songs: List[SongRecommendation]
    trending_instagram_audio: Optional[List[str]] = Field(default_factory=list)
    trending_tiktok_audio: Optional[List[str]] = Field(default_factory=list)
    trending_youtube_shorts_audio: Optional[List[str]] = Field(default_factory=list)
