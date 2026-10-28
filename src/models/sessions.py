import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String

from src.database import Base


class UserSession(Base):
    """One signed-in browser/device. The session cookie's token names this row,
    so logging out (or deleting the account) revokes it server-side."""

    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
