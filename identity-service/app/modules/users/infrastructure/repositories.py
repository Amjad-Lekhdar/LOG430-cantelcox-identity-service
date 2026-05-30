from uuid import UUID, uuid5, NAMESPACE_URL

from app.modules.users.domain.entities import User


class UserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._seed()

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

    def _seed(self) -> None:
        admin = User(
            id=uuid5(NAMESPACE_URL, "cantelcox.identity.admin"),
            email="admin@cantelcox.local",
            full_name="CanTelcoX Admin",
            role="admin",
        )
        self._users[admin.id] = admin


user_repository = UserRepository()
