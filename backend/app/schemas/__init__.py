from app.schemas.users import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserWithProfile,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    LocalAuthCreate,
    SocialAuthCreate,
    UserFavoriteCreate,
    UserFavoriteResponse,
)

from app.schemas.real_estate import (
    RegionCreate,
    RegionUpdate,
    RegionResponse,
    RealEstateCreate,
    RealEstateUpdate,
    RealEstateResponse,
    RealEstateWithTransactions,
    RealEstateWithRegion,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionWithRealEstate,
)

from app.schemas.trust import (
    TrustScoreCreate,
    TrustScoreUpdate,
    TrustScoreResponse,
)

from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionWithMessages,
    ChatMessageCreate,
    ChatMessageResponse,
)

__all__ = [
    # Users
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserWithProfile",
    "UserProfileCreate",
    "UserProfileUpdate",
    "UserProfileResponse",
    "LocalAuthCreate",
    "SocialAuthCreate",
    "UserFavoriteCreate",
    "UserFavoriteResponse",
    # Real Estate
    "RegionCreate",
    "RegionUpdate",
    "RegionResponse",
    "RealEstateCreate",
    "RealEstateUpdate",
    "RealEstateResponse",
    "RealEstateWithTransactions",
    "RealEstateWithRegion",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionWithRealEstate",
    # Trust
    "TrustScoreCreate",
    "TrustScoreUpdate",
    "TrustScoreResponse",
    # Chat
    "ChatSessionCreate",
    "ChatSessionUpdate",
    "ChatSessionResponse",
    "ChatSessionWithMessages",
    "ChatMessageCreate",
    "ChatMessageResponse",
]
