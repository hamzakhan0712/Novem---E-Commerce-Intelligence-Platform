from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import IndustryTemplate, StorePlatform


class CreateStoreRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    platform: StorePlatform = StorePlatform.OTHER
    url: Optional[str] = None
    currency: str = "INR"
    timezone: str = "UTC"
    industry: IndustryTemplate = IndustryTemplate.GENERAL
    description: Optional[str] = None


class UpdateStoreRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    platform: Optional[StorePlatform] = None
    url: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    industry: Optional[IndustryTemplate] = None
    description: Optional[str] = None


class StoreOut(BaseModel):
    id: str
    name: str
    platform: str
    url: Optional[str] = None
    currency: str
    timezone: str
    industry: str
    description: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
    data_summary: Optional["StoreDataCounts"] = None


class StoreDataCounts(BaseModel):
    orders: int = 0
    customers: int = 0
    products: int = 0
    ad_spend: int = 0
    reviews: int = 0
    stock_levels: int = 0
    total_imports: int = 0
    last_import_at: Optional[str] = None


class UserProfileOut(BaseModel):
    id: str
    name: str
    avatar_seed: Optional[str] = None
    email: Optional[str] = None
    currency: str
    region: str
    date_format: str
    fiscal_year_start: str
    timezone: str
    created_at: str
    updated_at: Optional[str] = None


class UpdateUserProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_seed: Optional[str] = None
    email: Optional[str] = None
    currency: Optional[str] = None
    region: Optional[str] = None
    date_format: Optional[str] = None
    fiscal_year_start: Optional[str] = None
    timezone: Optional[str] = None
