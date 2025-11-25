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

from app.schemas.region import (
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

from backend.app.schemas.housing_policy import (
    PolicyCategoryCreate,
    PolicyCategoryUpdate,
    PolicyCategoryResponse,
    PolicyCategoryWithChildren,
    PolicyTargetTypeCreate,
    PolicyTargetTypeUpdate,
    PolicyTargetTypeResponse,
    PolicyEligibilityRanksCreate,
    PolicyEligibilityRanksUpdate,
    PolicyEligibilityRanksResponse,
    PolicyFinancialSupportCreate,
    PolicyFinancialSupportUpdate,
    PolicyFinancialSupportResponse,
    PolicyContactCreate,
    PolicyContactUpdate,
    PolicyContactResponse,
    PolicyLinkCreate,
    PolicyLinkUpdate,
    PolicyLinkResponse,
    HousingPolicyCreate,
    HousingPolicyUpdate,
    HousingPolicyResponse,
    HousingPolicyWithDetails,
)

from app.schemas.checkpoint import (
    CheckPointCreate,
    CheckPointUpdate,
    CheckPointResponse,
    CheckPointBlobCreate,
    CheckPointBlobResponse,
    CheckPointWriteCreate,
    CheckPointWriteResponse,
)

from app.schemas.legal import (
    LawCreate,
    LawUpdate,
    LawResponse,
    LawWithArticles,
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    ArticleWithLaw,
    LegalReferenceCreate,
    LegalReferenceResponse,
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
    # Housing Policy
    "PolicyCategoryCreate",
    "PolicyCategoryUpdate",
    "PolicyCategoryResponse",
    "PolicyCategoryWithChildren",
    "PolicyTargetTypeCreate",
    "PolicyTargetTypeUpdate",
    "PolicyTargetTypeResponse",
    "PolicyEligibilityRanksCreate",
    "PolicyEligibilityRanksUpdate",
    "PolicyEligibilityRanksResponse",
    "PolicyFinancialSupportCreate",
    "PolicyFinancialSupportUpdate",
    "PolicyFinancialSupportResponse",
    "PolicyContactCreate",
    "PolicyContactUpdate",
    "PolicyContactResponse",
    "PolicyLinkCreate",
    "PolicyLinkUpdate",
    "PolicyLinkResponse",
    "HousingPolicyCreate",
    "HousingPolicyUpdate",
    "HousingPolicyResponse",
    "HousingPolicyWithDetails",
    # Checkpoint
    "CheckPointCreate",
    "CheckPointUpdate",
    "CheckPointResponse",
    "CheckPointBlobCreate",
    "CheckPointBlobResponse",
    "CheckPointWriteCreate",
    "CheckPointWriteResponse",
    # Legal
    "LawCreate",
    "LawUpdate",
    "LawResponse",
    "LawWithArticles",
    "ArticleCreate",
    "ArticleUpdate",
    "ArticleResponse",
    "ArticleWithLaw",
    "LegalReferenceCreate",
    "LegalReferenceResponse",
]
