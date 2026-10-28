from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    features = Column(String)
    is_active = Column(Boolean, default=True)

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime)

    user = relationship("User", backref="subscription")
    plan = relationship("SubscriptionPlan", backref="subscribers")
