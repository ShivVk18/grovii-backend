from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    Enum,
    String,
    Text
)
from sqlalchemy.sql import func
from src.database import Base
import enum
from sqlalchemy.orm import relationship
import uuid


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(
    String,
    primary_key=True,
    default=lambda:str(uuid.uuid4())
)

    status = Column(
        Enum(JobStatus),
        nullable=False,
        default=JobStatus.PENDING
    )

    user_id = Column(
    String,
    ForeignKey("users.id"),
    nullable=False
)

    storyboard_id = Column(

    String,

    ForeignKey(

        "storyboards.id"

    ),

    nullable=False

)
    
    queue_job_id = Column(

    String,

    nullable=True

)
    
    error_message = Column(

    Text,

    nullable=True

)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    user = relationship(
        "User",
        overlaps="jobs"
    )
    
    storyboard = relationship(
        "Storyboard",
        overlaps="jobs"
    )
    
    started_at = Column(

        DateTime

)
    
    progress = Column(

    Integer,

    default=0

)