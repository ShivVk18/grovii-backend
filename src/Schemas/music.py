from pydantic import BaseModel, Field
from typing import List, Optional


class SongRecommendation(BaseModel):
    song_name: str = Field(description="Actual song title that exists on Spotify/Apple Music")
    artist: str = Field(description="Actual performing artist or producer")
    why_fits: str = Field(description="Specific reason explaining how the song's BPM, tone, and genre amplify this exact video topic")
    best_scene: str = Field(description="Best scene placement in the video timeline (e.g. Scene 1-2, Fast-paced montage, Hook + Climax)")
    mood: str = Field(description="Specific mood and genre of the track (e.g. Cyberpunk Synthwave, Energetic Tech House, Chill Lo-fi, Cinematic Orchestral)")
    platform_popularity: Optional[str] = Field(default="Trending on Instagram Reels & TikTok", description="Platform viral status or trend indicator")
    royalty_free_alt: Optional[str] = Field(default="", description="High-quality royalty-free or stock track alternative for commercial use")


class MusicSuggestionOutput(BaseModel):
    songs: List[SongRecommendation]
    trending_instagram_audio: Optional[List[str]] = Field(default_factory=list)
    trending_tiktok_audio: Optional[List[str]] = Field(default_factory=list)
    trending_youtube_shorts_audio: Optional[List[str]] = Field(default_factory=list)

