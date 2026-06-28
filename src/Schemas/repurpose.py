from pydantic import BaseModel, Field

class RepurposeOutput(BaseModel):
    linkedin: str = Field(description="LinkedIn post content")
    twitter_thread: str = Field(description="Twitter thread content")
    carousel: str = Field(description="Carousel text content")
    blog: str = Field(description="Blog outline content")
    newsletter: str = Field(description="Email newsletter content")
