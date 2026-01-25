from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Storyboard(Base):
    __tablename__ = "storyboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    idea = Column(String, nullable=False)
    goal = Column(String, nullable=False)
    tone = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    audience = Column(String)

    output_json = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="storyboards")
