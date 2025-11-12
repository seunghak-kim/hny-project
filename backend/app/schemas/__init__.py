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
)

from app.schemas.building import (
    BuildingCreate,
    BuildingUpdate,
    BuildingResponse,
    BuildingWithDetails,
    BuildingFilter,
    BuildingListResponse,
)

from app.schemas.apartment import (
    ApartmentCreate,
    ApartmentUpdate,
    ApartmentResponse,
    ApartmentWithTransactions,
    ApartmentSaleTransactionCreate,
    ApartmentSaleTransactionUpdate,
    ApartmentSaleTransactionResponse,
    ApartmentRentTransactionCreate,
    ApartmentRentTransactionUpdate,
    ApartmentRentTransactionResponse,
)

from app.schemas.house import (
    HouseCreate,
    HouseUpdate,
    HouseResponse,
    HouseWithTransactions,
    HouseSaleTransactionCreate,
    HouseSaleTransactionUpdate,
    HouseSaleTransactionResponse,
    HouseRentTransactionCreate,
    HouseRentTransactionUpdate,
    HouseRentTransactionResponse,
)

from app.schemas.villa import (
    VillaCreate,
    VillaUpdate,
    VillaResponse,
    VillaWithTransactions,
    VillaSaleTransactionCreate,
    VillaSaleTransactionUpdate,
    VillaSaleTransactionResponse,
    VillaRentTransactionCreate,
    VillaRentTransactionUpdate,
    VillaRentTransactionResponse,
)

from app.schemas.officetel import (
    OfficetelCreate,
    OfficetelUpdate,
    OfficetelResponse,
    OfficetelWithTransactions,
    OfficetelSaleTransactionCreate,
    OfficetelSaleTransactionUpdate,
    OfficetelSaleTransactionResponse,
    OfficetelRentTransactionCreate,
    OfficetelRentTransactionUpdate,
    OfficetelRentTransactionResponse,
)

from app.schemas.transaction import (
    TransactionType,
    ContractType,
    DealingType,
    TransactionStats,
    SaleTransactionStats,
    RentTransactionStats,
    TransactionFilter,
    SaleTransactionFilter,
    RentTransactionFilter,
)

from app.schemas.trust import (
    TrustScoreCreate,
    TrustScoreUpdate,
    TrustScoreResponse,
)

from app.schemas.chat import (
    ChatSessionCreate,
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
    # Real Estate (Legacy)
    "RegionCreate",
    "RegionUpdate",
    "RegionResponse",
    # Building (건축물 통합 정보)
    "BuildingCreate",
    "BuildingUpdate",
    "BuildingResponse",
    "BuildingWithDetails",
    "BuildingFilter",
    "BuildingListResponse",
    # Apartment
    "ApartmentCreate",
    "ApartmentUpdate",
    "ApartmentResponse",
    "ApartmentWithTransactions",
    "ApartmentSaleTransactionCreate",
    "ApartmentSaleTransactionUpdate",
    "ApartmentSaleTransactionResponse",
    "ApartmentRentTransactionCreate",
    "ApartmentRentTransactionUpdate",
    "ApartmentRentTransactionResponse",
    # House
    "HouseCreate",
    "HouseUpdate",
    "HouseResponse",
    "HouseWithTransactions",
    "HouseSaleTransactionCreate",
    "HouseSaleTransactionUpdate",
    "HouseSaleTransactionResponse",
    "HouseRentTransactionCreate",
    "HouseRentTransactionUpdate",
    "HouseRentTransactionResponse",
    # Villa
    "VillaCreate",
    "VillaUpdate",
    "VillaResponse",
    "VillaWithTransactions",
    "VillaSaleTransactionCreate",
    "VillaSaleTransactionUpdate",
    "VillaSaleTransactionResponse",
    "VillaRentTransactionCreate",
    "VillaRentTransactionUpdate",
    "VillaRentTransactionResponse",
    # Officetel
    "OfficetelCreate",
    "OfficetelUpdate",
    "OfficetelResponse",
    "OfficetelWithTransactions",
    "OfficetelSaleTransactionCreate",
    "OfficetelSaleTransactionUpdate",
    "OfficetelSaleTransactionResponse",
    "OfficetelRentTransactionCreate",
    "OfficetelRentTransactionUpdate",
    "OfficetelRentTransactionResponse",
    # Transaction Common
    "TransactionType",
    "ContractType",
    "DealingType",
    "TransactionStats",
    "SaleTransactionStats",
    "RentTransactionStats",
    "TransactionFilter",
    "SaleTransactionFilter",
    "RentTransactionFilter",
    # Trust
    "TrustScoreCreate",
    "TrustScoreUpdate",
    "TrustScoreResponse",
    # Chat
    "ChatSessionCreate",
    "ChatSessionResponse",
    "ChatSessionWithMessages",
    "ChatMessageCreate",
    "ChatMessageResponse",
]
