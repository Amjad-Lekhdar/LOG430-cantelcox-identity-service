from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=160)
    role: str = Field(default="customer")


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
