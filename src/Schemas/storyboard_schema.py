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


class UpdateStoryboardRequest(BaseModel):
    title: Optional[str] = None
    idea: Optional[str] = None
    goal: Optional[str] = None
    tone: Optional[str] = None
    style: Optional[str] = None
    audience: Optional[str] = None
    duration: Optional[int] = None
    platform: Optional[str] = None


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

    created_at: datetime


    class Config:
        from_attributes = True