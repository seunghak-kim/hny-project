# Import all models to ensure they are registered with SQLAlchemy
from app.models.real_estate import RealEstate, Region, Transaction, NearbyFacility, RealEstateAgent
from app.models.trust import TrustScore
from app.models.users import User, UserProfile, LocalAuth, SocialAuth, UserFavorite
from app.models.chat import ChatSession, ChatMessage

__all__ = [
    "RealEstate",
    "Region",
    "Transaction",
    "NearbyFacility",
    "RealEstateAgent",
    "TrustScore",
    "User",
    "UserProfile",
    "LocalAuth",
    "SocialAuth",
    "UserFavorite",
    "ChatSession",
    "ChatMessage",
]
