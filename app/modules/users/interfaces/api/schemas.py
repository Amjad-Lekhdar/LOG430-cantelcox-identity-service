from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(
        validation_alias=AliasChoices("full_name", "fullName"),
        min_length=1,
        max_length=160,
    )
    role: str = Field(default="customer")


class CreateAccountRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(
        validation_alias=AliasChoices("full_name", "fullName"),
        min_length=1,
        max_length=160,
    )
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class LogoutResponse(BaseModel):
    logged_out: bool


class UpdateUserStatusRequest(BaseModel):
    active: bool


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    active: bool
    created_at: datetime
    updated_at: datetime
