# Import all models to ensure they are registered with SQLAlchemy
from app.models.real_estate import  Region
from app.models.building import Building
from app.models.apartment import Apartment, ApartmentSaleTransaction, ApartmentRentTransaction
from app.models.house import House, HouseSaleTransaction, HouseRentTransaction
from app.models.villa import Villa, VillaSaleTransaction, VillaRentTransaction
from app.models.officetel import Officetel, OfficetelSaleTransaction, OfficetelRentTransaction
from app.models.trust import TrustScore
from app.models.users import User, UserProfile, LocalAuth, SocialAuth, UserFavorite
from app.models.chat import ChatSession, ChatMessage

__all__ = [
    "Region",   
    # Building (건축물 통합 정보)
    "Building",
    # New separated models (새로운 분리 모델)
    "Apartment",
    "ApartmentSaleTransaction",
    "ApartmentRentTransaction",
    "House",
    "HouseSaleTransaction",
    "HouseRentTransaction",
    "Villa",
    "VillaSaleTransaction",
    "VillaRentTransaction",
    "Officetel",
    "OfficetelSaleTransaction",
    "OfficetelRentTransaction",
    # Other models
    "TrustScore",
    "User",
    "UserProfile",
    "LocalAuth",
    "SocialAuth",
    "UserFavorite",
    "ChatSession",
    "ChatMessage",
]
