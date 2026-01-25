from sqlalchemy import Column,String,Integer,DateTime 
from sqlalchemy.sql  import func 
from app.database import Base 

class User(Base):
    __tablename__  = "users"
    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
