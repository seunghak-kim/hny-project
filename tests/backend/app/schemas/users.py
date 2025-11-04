from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.users import Gender, SocialProvider
    
# ===== User Schemas =====
class UserBase(BaseModel):
    email: EmailStr = Field(..., description="이메일 (로그인 ID)")
    username: Optional[str] = Field(None, max_length=50, description="사용자 이름")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="비밀번호 (로컬 가입 시)")


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50, description="사용자 이름")
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int # BigInteger는 Python에서 int로 처리됩니다.
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== UserProfile Schemas =====
class UserProfileBase(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=20)
    bio: Optional[str] = Field(None, description="소개글")
    gender: Gender
    birth_date: str = Field(..., pattern=r'^\d{8}$')
    image_url: Optional[str] = None

    @field_validator('birth_date')
    def validate_birth_date(cls, v):
        current_year = int(datetime.now().year)
        try:
            year = int(v[:4])
            month = int(v[4:6])
            day = int(v[6:8])
            if not (1900 <= year <= current_year and 1 <= month <= 12 and 1 <= day <= 31):
                raise ValueError
        except (ValueError, IndexError):
            raise ValueError('Invalid birth_date format. Must be YYYYMMDD')
        return v


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=2, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
    gender: Optional[Gender] = None
    birth_date: Optional[str] = Field(None, pattern=r'^\d{8}$')
    image_url: Optional[str] = None


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== LocalAuth Schemas =====
class LocalAuthCreate(BaseModel):
    password: str = Field(..., min_length=8)


class LocalAuthResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    password_changed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== SocialAuth Schemas =====
class SocialAuthBase(BaseModel):
    provider: SocialProvider
    provider_id: str = Field(..., max_length=255, description="제공자가 준 고유 ID")
    provider_email: Optional[EmailStr] = Field(None, description="소셜 제공자 이메일")
    provider_name: Optional[str] = Field(None, max_length=100, description="소셜 제공자 이름")


class SocialAuthCreate(SocialAuthBase):
    pass


class SocialAuthResponse(SocialAuthBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== UserFavorite Schemas =====
class UserFavoriteCreate(BaseModel):
    real_estate_id: int


class UserFavoriteResponse(BaseModel):
    id: int
    user_id: int
    real_estate_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Combined User with Profile =====
class UserDetailResponse(UserResponse):
    profile: Optional[UserProfileResponse] = None
    social_auths: List[SocialAuthResponse] = []
    favorites: List[UserFavoriteResponse] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None