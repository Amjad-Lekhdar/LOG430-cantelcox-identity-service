from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.modules.users.application.use_cases import (
    CreateUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserStatusUseCase,
)
from app.modules.users.infrastructure.repositories import user_repository
from app.modules.users.interfaces.api.schemas import (
    CreateUserRequest,
    UpdateUserStatusRequest,
    UserResponse,
)

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest) -> UserResponse:
    try:
        user = CreateUserUseCase(user_repository).execute(
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return UserResponse(**user.__dict__)


@router.get("", response_model=list[UserResponse])
def list_users(active_only: bool = False) -> list[UserResponse]:
    users = ListUsersUseCase(user_repository).execute(active_only=active_only)
    return [UserResponse(**user.__dict__) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID) -> UserResponse:
    user = GetUserUseCase(user_repository).execute(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user.__dict__)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(user_id: UUID, payload: UpdateUserStatusRequest) -> UserResponse:
    user = UpdateUserStatusUseCase(user_repository).execute(user_id=user_id, active=payload.active)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user.__dict__)
