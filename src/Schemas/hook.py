from pydantic import BaseModel, Field
from typing import List

class HookOption(BaseModel):
    hook: str = Field(description="The regenerated hook text")
    type: str = Field(description="The type of the hook (e.g., Curiosity, Emotional, Contrarian, Storytelling, FOMO)")
    score: int = Field(description="The predicted score out of 100")

class HookRegeneratorOutput(BaseModel):
    regenerated_hooks: List[HookOption]
