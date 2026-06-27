from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(
        validation_alias=AliasChoices("full_name", "fullName"),
        min_length=1,
        max_length=160,
    )
    phone_number: str | None = Field(
        default=None,
        validation_alias=AliasChoices("phone_number", "phoneNumber", "phone"),
        max_length=40,
    )
    role: str = Field(default="customer")


class CreateAccountRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(
        validation_alias=AliasChoices("full_name", "fullName"),
        min_length=1,
        max_length=160,
    )
    phone_number: str | None = Field(
        default=None,
        validation_alias=AliasChoices("phone_number", "phoneNumber", "phone"),
        max_length=40,
    )
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class MfaChallengeResponse(BaseModel):
    mfa_required: bool = True
    challenge_id: str
    user_id: UUID | None = None
    login_token: str | None = None
    token_login: str | None = None
    expires_at: datetime
    channel: str = "simulated"
    destination: str | None = None
    remaining_attempts: int
    debug_otp: str | None = None


class MfaRequest(BaseModel):
    user_id: UUID = Field(validation_alias=AliasChoices("user_id", "userId"))
    channel: Literal["sms", "email"]
    destination: str = Field(min_length=3, max_length=255)


class VerifyMfaRequest(BaseModel):
    challenge_id: str = Field(validation_alias=AliasChoices("challenge_id", "challengeId"))
    code: str = Field(min_length=4, max_length=12)


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    logged_out: bool


class UpdateUserStatusRequest(BaseModel):
    active: bool


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone_number: str | None = None
    role: str
    active: bool
    created_at: datetime
    updated_at: datetime
