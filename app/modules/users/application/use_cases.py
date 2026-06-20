import logging
import os
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from app.modules.users.domain.entities import MfaChallenge, User
from app.modules.users.domain.services import MfaService, PasswordService, UserDomainService
from app.modules.users.domain.value_objects import UserRole
from app.modules.users.infrastructure.repositories import (
    AuthSessionRepository,
    MfaChallengeRepository,
    MfaLoginTokenRepository,
)

logger = logging.getLogger(__name__)


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


@dataclass
class MfaChallengeResult:
    challenge: MfaChallenge
    code: str | None = None
    login_token: str | None = None
    user: User | None = None
    channel: str = "simulated"
    destination: str | None = None


@dataclass
class MfaVerificationResult:
    status: str
    user: User | None = None
    access_token: str | None = None
    remaining_attempts: int | None = None


class CreateUserUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, email: str, full_name: str, role: str, phone_number: str | None = None) -> User:
        normalized_email = UserDomainService.normalize_email(email)
        normalized_phone_number = UserDomainService.normalize_phone_number(phone_number)
        UserRole(role)
        UserDomainService.ensure_email_is_available(
            self._repository.get_by_email(normalized_email),
            normalized_email,
        )
        user = User(
            id=uuid4(),
            email=normalized_email,
            full_name=full_name,
            phone_number=normalized_phone_number,
            role=role,
        )
        return self._repository.add(user)


class CreateAccountUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(
        self,
        email: str,
        full_name: str,
        password: str,
        phone_number: str | None = None,
        role: str = "customer",
    ) -> User:
        normalized_email = UserDomainService.normalize_email(email)
        normalized_phone_number = UserDomainService.normalize_phone_number(phone_number)
        UserRole(role)
        UserDomainService.ensure_email_is_available(
            self._repository.get_by_email(normalized_email),
            normalized_email,
        )
        user = User(
            id=uuid4(),
            email=normalized_email,
            full_name=full_name,
            phone_number=normalized_phone_number,
            role=role,
            password_hash=PasswordService.hash_password(password),
        )
        return self._repository.add(user)


class LoginUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        mfa_repository: MfaChallengeRepository,
        login_token_repository: MfaLoginTokenRepository,
    ) -> None:
        self._user_repository = user_repository
        self._mfa_repository = mfa_repository
        self._login_token_repository = login_token_repository

    def execute(self, email: str, password: str) -> MfaChallengeResult | None:
        normalized_email = UserDomainService.normalize_email(email)
        user = self._user_repository.get_by_email(normalized_email)
        if user is None or not user.active:
            logger.info("auth.login.failed")
            return None
        if not PasswordService.verify_password(password, user.password_hash):
            logger.info("auth.login.failed")
            return None
        code = MfaService.generate_code()
        challenge = self._mfa_repository.create(user.id, code)
        login_token = self._login_token_repository.create(user.id)
        logger.info("auth.mfa.challenge_created", extra={"user_id": str(user.id)})
        debug_code = code if os.getenv("MFA_DEBUG_OTP", "true").lower() == "true" else None
        return MfaChallengeResult(
            challenge=challenge,
            code=debug_code,
            login_token=login_token,
            user=user,
        )


class RequestMfaUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        mfa_repository: MfaChallengeRepository,
        login_token_repository: MfaLoginTokenRepository,
    ) -> None:
        self._user_repository = user_repository
        self._mfa_repository = mfa_repository
        self._login_token_repository = login_token_repository

    def execute(
        self,
        login_token: str,
        user_id: UUID,
        channel: str,
        destination: str,
    ) -> MfaChallengeResult | None:
        token_user_id = self._login_token_repository.get_user_id(login_token)
        if token_user_id is None or token_user_id != user_id:
            logger.info("auth.mfa.request.invalid_login_token")
            return None

        user = self._user_repository.get(user_id)
        if user is None or not user.active:
            logger.info("auth.mfa.request.user_missing_or_inactive", extra={"user_id": str(user_id)})
            return None

        normalized_channel = channel.strip().lower()
        normalized_destination = destination.strip()
        if normalized_channel not in {"sms", "email"}:
            raise ValueError("MFA channel must be sms or email")
        if normalized_channel == "email" and normalized_destination.lower() != user.email:
            raise ValueError("MFA email destination must match the user profile")
        if normalized_channel == "sms":
            normalized_phone_number = UserDomainService.normalize_phone_number(normalized_destination)
            if user.phone_number is None or normalized_phone_number != user.phone_number:
                raise ValueError("MFA SMS destination must match the user profile")

        code = MfaService.generate_code()
        challenge = self._mfa_repository.create(user.id, code)
        logger.info(
            "auth.mfa.request.created",
            extra={"user_id": str(user.id), "channel": normalized_channel},
        )
        debug_code = code if os.getenv("MFA_DEBUG_OTP", "true").lower() == "true" else None
        return MfaChallengeResult(
            challenge=challenge,
            code=debug_code,
            user=user,
            channel=normalized_channel,
            destination=normalized_destination,
        )


class VerifyMfaUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: AuthSessionRepository,
        mfa_repository: MfaChallengeRepository,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._mfa_repository = mfa_repository

    def execute(self, challenge_id: str, code: str) -> MfaVerificationResult:
        challenge = self._mfa_repository.get(challenge_id)
        if challenge is None:
            logger.info("auth.mfa.invalid_or_expired_challenge")
            return MfaVerificationResult(status="invalid")
        if challenge.blocked:
            logger.warning("auth.mfa.blocked", extra={"user_id": str(challenge.user_id)})
            return MfaVerificationResult(status="blocked", remaining_attempts=0)
        if not MfaService.verify_code(code, challenge.code_hash):
            challenge = self._mfa_repository.record_failed_attempt(challenge)
            remaining_attempts = max(challenge.max_attempts - challenge.attempts, 0)
            if challenge.blocked:
                logger.warning("auth.mfa.max_attempts_reached", extra={"user_id": str(challenge.user_id)})
                return MfaVerificationResult(status="blocked", remaining_attempts=0)
            logger.info("auth.mfa.failed", extra={"user_id": str(challenge.user_id)})
            return MfaVerificationResult(status="invalid", remaining_attempts=remaining_attempts)
        user = self._user_repository.get(challenge.user_id)
        if user is None or not user.active:
            logger.info("auth.mfa.user_missing_or_inactive", extra={"user_id": str(challenge.user_id)})
            return MfaVerificationResult(status="invalid")
        self._mfa_repository.delete(challenge.id)
        access_token = self._session_repository.create(user.id)
        logger.info("auth.mfa.succeeded", extra={"user_id": str(user.id)})
        return MfaVerificationResult(status="success", user=user, access_token=access_token)


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
