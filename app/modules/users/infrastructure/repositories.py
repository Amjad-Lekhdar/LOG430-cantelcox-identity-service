import secrets
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.domain.services import MfaService, PasswordService
from app.modules.users.domain.entities import MfaChallenge, User
from app.modules.users.infrastructure.models import UserModel


class SQLAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        model = self._to_model(user)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, str(user.id))
        if model is None:
            return self.add(user)
        model.email = user.email
        model.full_name = user.full_name
        model.phone_number = user.phone_number
        model.role = user.role
        model.password_hash = user.password_hash
        model.active = user.active
        model.updated_at = user.updated_at
        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    def list(self) -> list[User]:
        models = self._session.scalars(select(UserModel).order_by(UserModel.created_at)).all()
        return [self._to_domain(model) for model in models]

    def get(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, str(user_id))
        if model is None:
            return None
        return self._to_domain(model)

    def get_by_email(self, email: str) -> User | None:
        normalized_email = email.strip().lower()
        model = self._session.scalar(select(UserModel).where(UserModel.email == normalized_email))
        if model is None:
            return None
        return self._to_domain(model)

    @staticmethod
    def _to_model(user: User) -> UserModel:
        return UserModel(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            phone_number=user.phone_number,
            role=user.role,
            password_hash=user.password_hash,
            active=user.active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=UUID(model.id),
            email=model.email,
            full_name=model.full_name,
            phone_number=model.phone_number,
            role=model.role,
            password_hash=model.password_hash,
            active=model.active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def seed_admin_user(session: Session) -> None:
    repository = SQLAlchemyUserRepository(session)
    if repository.get_by_email("admin@cantelcox.local") is not None:
        return

    admin = User(
        id=uuid5(NAMESPACE_URL, "cantelcox.identity.admin"),
        email="admin@cantelcox.local",
        full_name="CanTelcoX Admin",
        role="admin",
        password_hash=PasswordService.hash_password("admin12345"),
    )
    repository.add(admin)


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    def add(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def update(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def list(self) -> list[User]:
        return list(self._users.values())

    def get(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized_email = email.strip().lower()
        return next((user for user in self._users.values() if user.email == normalized_email), None)


class AuthSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, UUID] = {}

    def create(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user_id
        return token

    def get_user_id(self, token: str) -> UUID | None:
        return self._sessions.get(token)

    def delete(self, token: str) -> bool:
        return self._sessions.pop(token, None) is not None


class MfaLoginTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, UUID] = {}

    def create(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = user_id
        return token

    def get_user_id(self, token: str) -> UUID | None:
        return self._tokens.get(token)

    def delete(self, token: str) -> bool:
        return self._tokens.pop(token, None) is not None


class MfaChallengeRepository:
    def __init__(self, ttl_seconds: int = 300, max_attempts: int = 3) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_attempts = max_attempts
        self._challenges: dict[str, MfaChallenge] = {}

    def create(self, user_id: UUID, code: str) -> MfaChallenge:
        challenge = MfaChallenge(
            id=secrets.token_urlsafe(24),
            user_id=user_id,
            code_hash=MfaService.hash_code(code),
            expires_at=MfaService.expires_at(self._ttl_seconds),
            max_attempts=self._max_attempts,
        )
        self._challenges[challenge.id] = challenge
        return challenge

    def get(self, challenge_id: str) -> MfaChallenge | None:
        challenge = self._challenges.get(challenge_id)
        if challenge is None:
            return None
        if challenge.expires_at <= datetime.now(timezone.utc):
            self.delete(challenge_id)
            return None
        return challenge

    def record_failed_attempt(self, challenge: MfaChallenge) -> MfaChallenge:
        challenge.attempts += 1
        if challenge.attempts >= challenge.max_attempts:
            challenge.blocked = True
        self._challenges[challenge.id] = challenge
        return challenge

    def delete(self, challenge_id: str) -> bool:
        return self._challenges.pop(challenge_id, None) is not None


auth_session_repository = AuthSessionRepository()
mfa_login_token_repository = MfaLoginTokenRepository()
mfa_challenge_repository = MfaChallengeRepository()
