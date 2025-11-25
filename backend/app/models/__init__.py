# Import all models to ensure they are registered with SQLAlchemy
from app.models.region import Region
from app.models.building import Building
from app.models.infrastructure import Infrastructure
from app.models.trust import TrustScore
from app.models.auth.users import User, UserProfile, LocalAuth, SocialAuth, UserFavorite
from app.models.chat import ChatSession, ChatMessage

# Transaction models
from app.models.transaction.transaction import Transaction
from app.models.transaction.sale_transaction import SaleTransaction
from app.models.transaction.rent_transaction import RentTransaction
from app.models.transaction.apartment import ApartmentSaleTransaction
from app.models.transaction.villa import VillaSaleTransaction
from app.models.transaction.house import HouseSaleTransaction

# Policy models
from app.models.policy.housing_policy import (
    PolicyCategory,
    HousingPolicy,
    PolicyTargetType,
    PolicyEligibilityRanks,
    PolicyFinancialSupport,
    PolicyContact,
    PolicyLink
)

__all__ = [
    # Region & Building
    "Region",
    "Building",
    "Infrastructure",

    # Transaction models
    "Transaction",
    "SaleTransaction",
    "RentTransaction",
    "ApartmentSaleTransaction",
    "VillaSaleTransaction",
    "HouseSaleTransaction",

    # User models
    "TrustScore",
    "User",
    "UserProfile",
    "LocalAuth",
    "SocialAuth",
    "UserFavorite",

    # Chat models
    "ChatSession",
    "ChatMessage",

    # Policy models
    "PolicyCategory",
    "HousingPolicy",
    "PolicyTargetType",
    "PolicyEligibilityRanks",
    "PolicyFinancialSupport",
    "PolicyContact",
    "PolicyLink",
]
