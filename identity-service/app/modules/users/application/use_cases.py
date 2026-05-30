from uuid import UUID, uuid4

from app.modules.users.domain.entities import User
from app.modules.users.domain.services import UserDomainService
from app.modules.users.domain.value_objects import UserRole
from app.modules.users.infrastructure.repositories import UserRepository


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
