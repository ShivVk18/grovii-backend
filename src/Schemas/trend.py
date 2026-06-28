from pydantic import BaseModel, Field
from typing import List

class TrendAnalyzerOutput(BaseModel):
    hooks: List[str] = Field(description="List of suggested hooks based on trends", default_factory=list)
    sounds: List[str] = Field(description="List of suggested trending sounds", default_factory=list)
    transitions: List[str] = Field(description="List of suggested transitions", default_factory=list)
    best_duration: str = Field(description="The best duration for the video")
    posting_time: str = Field(description="The optimal posting time")
    editing_style: str = Field(description="Suggested editing style")
    content_gaps: List[str] = Field(description="List of content gaps found in the trend", default_factory=list)
