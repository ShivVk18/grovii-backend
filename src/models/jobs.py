import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    false,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


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

    # Credits taken from the user for this job, and whether they were given back.
    credits_charged = Column(Integer, nullable=False, default=0, server_default="0")
    credits_refunded = Column(Boolean, nullable=False, default=False, server_default=false())

    # LLM usage for this job, recorded when it finishes (success or failure).
    # cost_usd is an estimate from token counts x configured prices; NULL means
    # not recorded yet (job still queued or running).
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    llm_calls = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(12, 6), nullable=True)