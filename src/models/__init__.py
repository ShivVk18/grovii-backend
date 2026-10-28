# Import all models so Base.metadata knows about them and SQLAlchemy mappers resolve relationships
from src.models import indexes  # noqa: F401  (registers indexes on the tables)
from src.models.caption import Caption
from src.models.hashtag import Hashtag
from src.models.hook import Hook
from src.models.jobs import Job
from src.models.music import MusicSuggestion
from src.models.repurpose import RepurposeContent
from src.models.scenes import Scene
from src.models.sessions import UserSession
from src.models.storyboard import Storyboard
from src.models.subscription import SubscriptionPlan, UserSubscription
from src.models.trend import Trend
from src.models.users import User

__all__ = [
    "User",
    "Storyboard",
    "Scene",
    "Caption",
    "Hashtag",
    "Hook",
    "Job",
    "MusicSuggestion",
    "RepurposeContent",
    "Trend",
    "SubscriptionPlan",
    "UserSubscription",
    "UserSession",
]
