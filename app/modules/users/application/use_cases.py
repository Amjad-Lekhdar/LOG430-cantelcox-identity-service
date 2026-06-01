from typing import Protocol
from uuid import UUID, uuid4

from app.modules.users.domain.entities import User
from app.modules.users.domain.services import PasswordService, UserDomainService
from app.modules.users.domain.value_objects import UserRole
from app.modules.users.infrastructure.repositories import AuthSessionRepository


class UserRepository(Protocol):
    def add(self, user: User) -> User:
        pass

    def update(self, user: User) -> User:
        pass

    def list(self) -> list[User]:
        pass

    def get(self, user_id: UUID) -> User | None:
        pass

    def get_by_email(self, email: str) -> User | None:
        pass


class CreateUserUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, email: str, full_name: str, role: str) -> User:
        normalized_email = UserDomainService.normalize_email(email)
        UserRole(role)
        UserDomainService.ensure_email_is_available(
            self._repository.get_by_email(normalized_email),
            normalized_email,
        )
        user = User(id=uuid4(), email=normalized_email, full_name=full_name, role=role)
        return self._repository.add(user)


class CreateAccountUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, email: str, full_name: str, password: str, role: str = "customer") -> User:
        normalized_email = UserDomainService.normalize_email(email)
        UserRole(role)
        UserDomainService.ensure_email_is_available(
            self._repository.get_by_email(normalized_email),
            normalized_email,
        )
        user = User(
            id=uuid4(),
            email=normalized_email,
            full_name=full_name,
            role=role,
            password_hash=PasswordService.hash_password(password),
        )
        return self._repository.add(user)


class LoginUseCase:
    def __init__(self, user_repository: UserRepository, session_repository: AuthSessionRepository) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository

    def execute(self, email: str, password: str) -> tuple[User, str] | None:
        normalized_email = UserDomainService.normalize_email(email)
        user = self._user_repository.get_by_email(normalized_email)
        if user is None or not user.active:
            return None
        if not PasswordService.verify_password(password, user.password_hash):
            return None
        token = self._session_repository.create(user.id)
        return user, token


class LogoutUseCase:
    def __init__(self, session_repository: AuthSessionRepository) -> None:
        self._session_repository = session_repository

    def execute(self, token: str) -> bool:
        return self._session_repository.delete(token)


class ListUsersUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, active_only: bool = False) -> list[User]:
        users = self._repository.list()
        if active_only:
            return [user for user in users if user.active]
        return users


class GetUserUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, user_id: UUID) -> User | None:
        return self._repository.get(user_id)


class UpdateUserStatusUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, user_id: UUID, active: bool) -> User | None:
        user = self._repository.get(user_id)
        if user is None:
            return None
        user.set_active(active)
        return self._repository.update(user)
