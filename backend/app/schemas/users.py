from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.users import UserType, Gender, SocialProvider


# ===== User Schemas =====
class UserBase(BaseModel):
    email: EmailStr
    type: UserType = UserType.USER


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== UserProfile Schemas =====
class UserProfileBase(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
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
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===== LocalAuth Schemas =====
class LocalAuthCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LocalAuthResponse(BaseModel):
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== SocialAuth Schemas =====
class SocialAuthBase(BaseModel):
    provider: SocialProvider
    provider_user_id: str


class SocialAuthCreate(SocialAuthBase):
    email: EmailStr


class SocialAuthResponse(SocialAuthBase):
    id: int
    user_id: int
    created_at: datetime

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
class UserWithProfile(UserResponse):
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True
