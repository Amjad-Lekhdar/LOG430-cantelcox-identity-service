from typing import Protocol
from uuid import UUID

from app.modules.users.domain.entities import MfaChallenge, User


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


class AuthSessionRepository(Protocol):
    def create(self, user_id: UUID) -> str:
        pass

    def get_user_id(self, token: str) -> UUID | None:
        pass

    def delete(self, token: str) -> bool:
        pass


class MfaLoginTokenRepository(Protocol):
    def create(self, user_id: UUID) -> str:
        pass

    def get_user_id(self, token: str) -> UUID | None:
        pass

    def delete(self, token: str) -> bool:
        pass


class MfaChallengeRepository(Protocol):
    def create(self, user_id: UUID, code: str) -> MfaChallenge:
        pass

    def get(self, challenge_id: str) -> MfaChallenge | None:
        pass

    def record_failed_attempt(self, challenge: MfaChallenge) -> MfaChallenge:
        pass

    def delete(self, challenge_id: str) -> bool:
        pass
