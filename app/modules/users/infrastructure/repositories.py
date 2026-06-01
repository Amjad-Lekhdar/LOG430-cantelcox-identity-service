import secrets
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.domain.services import PasswordService
from app.modules.users.domain.entities import User
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


auth_session_repository = AuthSessionRepository()
