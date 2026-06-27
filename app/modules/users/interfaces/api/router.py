from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.modules.users.application.use_cases import (
    CreateAccountUseCase,
    CreateUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    LoginUseCase,
    LogoutUseCase,
    RequestMfaUseCase,
    UpdateUserStatusUseCase,
    VerifyMfaUseCase,
)
from app.modules.users.infrastructure.repositories import (
    SQLAlchemyUserRepository,
    auth_session_repository,
    mfa_challenge_repository,
    mfa_login_token_repository,
)
from app.modules.users.interfaces.api.schemas import (
    AuthResponse,
    CreateAccountRequest,
    CreateUserRequest,
    LoginRequest,
    MfaChallengeResponse,
    MfaRequest,
    OAuthTokenResponse,
    LogoutResponse,
    UpdateUserStatusRequest,
    UserResponse,
    VerifyMfaRequest,
)

router = APIRouter(prefix="/v1/users", tags=["Users"])
auth_router = APIRouter(prefix="/v1/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


def get_user_repository(session: Session = Depends(get_db_session)) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


def _user_response(user) -> UserResponse:
    return UserResponse(**user.__dict__)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    user_id = auth_session_repository.get_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user_repository.get(user_id)
    if user is None or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or missing user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user_response(user)


@auth_router.post("/accounts", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: CreateAccountRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    try:
        user = CreateAccountUseCase(user_repository).execute(
            email=payload.email,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _user_response(user)


@auth_router.post("/login", response_model=MfaChallengeResponse)
def login(
    payload: LoginRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> MfaChallengeResponse:
    try:
        result = LoginUseCase(
            user_repository,
            mfa_challenge_repository,
            mfa_login_token_repository,
        ).execute(
            email=payload.email,
            password=payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return MfaChallengeResponse(
        challenge_id=result.challenge.id,
        user_id=result.user.id if result.user is not None else None,
        login_token=result.login_token,
        token_login=result.login_token,
        token=result.login_token,
        expires_at=result.challenge.expires_at,
        remaining_attempts=result.challenge.max_attempts,
        debug_otp=result.code,
    )


@auth_router.post("/mfa/request", response_model=MfaChallengeResponse)
def request_mfa(
    payload: MfaRequest,
    login_token: str = Depends(oauth2_scheme),
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> MfaChallengeResponse:
    try:
        result = RequestMfaUseCase(
            user_repository,
            mfa_challenge_repository,
            mfa_login_token_repository,
        ).execute(
            login_token=login_token,
            user_id=payload.user_id,
            channel=payload.channel,
            destination=payload.destination,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA login token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return MfaChallengeResponse(
        challenge_id=result.challenge.id,
        user_id=payload.user_id,
        expires_at=result.challenge.expires_at,
        channel=result.channel,
        destination=result.destination,
        remaining_attempts=result.challenge.max_attempts,
        debug_otp=result.code,
    )


@auth_router.post("/mfa/verify", response_model=AuthResponse)
def verify_mfa(
    payload: VerifyMfaRequest,
    user_repository: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> AuthResponse:
    result = VerifyMfaUseCase(
        user_repository,
        auth_session_repository,
        mfa_challenge_repository,
    ).execute(challenge_id=payload.challenge_id, code=payload.code)
    if result.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maximum MFA attempts reached; validation is temporarily blocked",
        )
    if result.status != "success" or result.user is None or result.access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA code",
        )
    return AuthResponse(access_token=result.access_token, user=_user_response(result.user))


@auth_router.post("/token", response_model=OAuthTokenResponse)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> OAuthTokenResponse:
    _ = form_data
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="MFA required; use /v1/auth/login then /v1/auth/mfa/verify",
    )


@auth_router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user


@auth_router.post("/logout", response_model=LogoutResponse)
def logout(token: str = Depends(oauth2_scheme)) -> LogoutResponse:
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
            phone_number=payload.phone_number,
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
