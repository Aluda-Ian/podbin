from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class ProviderTier(str, Enum):
    PLATFORM_FREE = "PLATFORM_FREE"
    PLATFORM_PAID = "PLATFORM_PAID"
    BYO_KEY = "BYO_KEY"

class ProviderConfig(BaseModel):
    tier: ProviderTier = ProviderTier.PLATFORM_FREE
    custom_api_key: Optional[str] = None
    custom_provider: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str  # "Super Admin" | "Podcast Owner" | "Team Member"
    podcast_ids: List[str]
    provider_config: Optional[ProviderConfig] = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name: str
    email: str
    role: str
    password: str = "password123"
    podcast_ids: List[str] = Field(default_factory=list)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    podcast_ids: Optional[List[str]] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
