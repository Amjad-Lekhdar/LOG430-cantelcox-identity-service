from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.modules.users.application.use_cases import (
    CreateAccountUseCase,
    CreateUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    LoginUseCase,
    LogoutUseCase,
    UpdateUserStatusUseCase,
)
from app.modules.users.infrastructure.repositories import SQLAlchemyUserRepository, auth_session_repository
from app.modules.users.interfaces.api.schemas import (
    AuthResponse,
    CreateAccountRequest,
    CreateUserRequest,
    LoginRequest,
    LogoutResponse,
    UpdateUserStatusRequest,
    UserResponse,
)

router = APIRouter(prefix="/v1/users", tags=["Users"])
auth_router = APIRouter(prefix="/v1/auth", tags=["Auth"])


def get_user_repository(session: Session = Depends(get_db_session)) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


def _user_response(user) -> UserResponse:
    return UserResponse(**user.__dict__)


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer token is required")
    return token


@auth_router.post("/accounts", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: CreateAccountRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = CreateAccountUseCase(user_repository).execute(
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _user_response(user)


@auth_router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> AuthResponse:
    try:
        result = LoginUseCase(user_repository, auth_session_repository).execute(
            email=payload.email,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user, token = result
    return AuthResponse(access_token=token, user=_user_response(user))


@auth_router.post("/logout", response_model=LogoutResponse)
def logout(authorization: str | None = Header(default=None)) -> LogoutResponse:
    token = _extract_bearer_token(authorization)
    logged_out = LogoutUseCase(auth_session_repository).execute(token)
    if not logged_out:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return LogoutResponse(logged_out=True)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = CreateUserUseCase(user_repository).execute(
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _user_response(user)


@router.get("", response_model=list[UserResponse])
def list_users(
    active_only: bool = False,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> list[UserResponse]:
    users = ListUsersUseCase(user_repository).execute(active_only=active_only)
    return [_user_response(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    user = GetUserUseCase(user_repository).execute(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response(user)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: UUID,
    payload: UpdateUserStatusRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    user = UpdateUserStatusUseCase(user_repository).execute(user_id=user_id, active=payload.active)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response(user)
