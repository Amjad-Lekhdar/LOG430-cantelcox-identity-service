from uuid import uuid4

import pytest

from app.modules.users.application.use_cases import (
    CreateAccountUseCase,
    CreateUserUseCase,
    ListUsersUseCase,
    LoginUseCase,
    RequestMfaUseCase,
    UpdateUserStatusUseCase,
    VerifyMfaUseCase,
)
from app.modules.users.infrastructure.repositories import (
    AuthSessionRepository,
    InMemoryUserRepository,
    MfaChallengeRepository,
    MfaLoginTokenRepository,
)


@pytest.fixture
def repositories() -> tuple[
    InMemoryUserRepository,
    AuthSessionRepository,
    MfaLoginTokenRepository,
    MfaChallengeRepository,
]:
    return (
        InMemoryUserRepository(),
        AuthSessionRepository(),
        MfaLoginTokenRepository(),
        MfaChallengeRepository(max_attempts=2),
    )


def test_create_user_normalizes_fields_and_rejects_duplicate_email(
    repositories: tuple[
        InMemoryUserRepository,
        AuthSessionRepository,
        MfaLoginTokenRepository,
        MfaChallengeRepository,
    ],
) -> None:
    user_repository, _, _, _ = repositories
    use_case = CreateUserUseCase(user_repository)

    user = use_case.execute(
        email=" JANE@EXAMPLE.COM ",
        full_name="Jane Client",
        role="customer",
        phone_number=" +1 514 555 0101 ",
    )

    assert user.email == "jane@example.com"
    assert user.phone_number == "+1 514 555 0101"

    with pytest.raises(ValueError, match="already exists"):
        use_case.execute("jane@example.com", "Jane Duplicate", "customer")


def test_login_requires_active_user_and_valid_password(
    repositories: tuple[
        InMemoryUserRepository,
        AuthSessionRepository,
        MfaLoginTokenRepository,
        MfaChallengeRepository,
    ],
) -> None:
    user_repository, _, login_token_repository, mfa_repository = repositories
    user = CreateAccountUseCase(user_repository).execute(
        "jane@example.com",
        "Jane Client",
        "password123",
        phone_number="+1 514 555 0101",
    )
    use_case = LoginUseCase(user_repository, mfa_repository, login_token_repository)

    result = use_case.execute(" JANE@example.com ", "password123")

    assert result is not None
    assert result.user == user
    assert result.login_token is not None
    assert result.code is not None
    assert use_case.execute("jane@example.com", "wrong-password") is None

    user.active = False
    user_repository.update(user)

    assert use_case.execute("jane@example.com", "password123") is None


def test_request_mfa_validates_token_channel_and_destination(
    repositories: tuple[
        InMemoryUserRepository,
        AuthSessionRepository,
        MfaLoginTokenRepository,
        MfaChallengeRepository,
    ],
) -> None:
    user_repository, _, login_token_repository, mfa_repository = repositories
    user = CreateAccountUseCase(user_repository).execute(
        "jane@example.com",
        "Jane Client",
        "password123",
        phone_number="+1 514 555 0101",
    )
    login_token = login_token_repository.create(user.id)
    use_case = RequestMfaUseCase(user_repository, mfa_repository, login_token_repository)

    result = use_case.execute(login_token, user.id, " SMS ", " +1 514 555 0101 ")

    assert result is not None
    assert result.user == user
    assert result.channel == "sms"
    assert result.destination == "+1 514 555 0101"
    assert use_case.execute("bad-token", user.id, "sms", "+1 514 555 0101") is None

    with pytest.raises(ValueError, match="MFA channel must be sms or email"):
        use_case.execute(login_token, user.id, "push", "+1 514 555 0101")

    with pytest.raises(ValueError, match="MFA email destination must match"):
        use_case.execute(login_token, user.id, "email", "other@example.com")


def test_verify_mfa_success_invalid_and_blocked_paths(
    repositories: tuple[
        InMemoryUserRepository,
        AuthSessionRepository,
        MfaLoginTokenRepository,
        MfaChallengeRepository,
    ],
) -> None:
    user_repository, session_repository, _, mfa_repository = repositories
    user = CreateAccountUseCase(user_repository).execute(
        "jane@example.com",
        "Jane Client",
        "password123",
    )
    challenge = mfa_repository.create(user.id, "123456")
    use_case = VerifyMfaUseCase(user_repository, session_repository, mfa_repository)

    invalid_result = use_case.execute(challenge.id, "000000")

    assert invalid_result.status == "invalid"
    assert invalid_result.remaining_attempts == 1

    blocked_result = use_case.execute(challenge.id, "000000")

    assert blocked_result.status == "blocked"
    assert blocked_result.remaining_attempts == 0

    challenge = mfa_repository.create(user.id, "123456")
    success_result = use_case.execute(challenge.id, "123456")

    assert success_result.status == "success"
    assert success_result.user == user
    assert success_result.access_token is not None
    assert session_repository.get_user_id(success_result.access_token) == user.id


def test_list_and_update_user_status(
    repositories: tuple[
        InMemoryUserRepository,
        AuthSessionRepository,
        MfaLoginTokenRepository,
        MfaChallengeRepository,
    ],
) -> None:
    user_repository, _, _, _ = repositories
    active_user = CreateUserUseCase(user_repository).execute("a@example.com", "Active", "agent")
    inactive_user = CreateUserUseCase(user_repository).execute("b@example.com", "Inactive", "agent")

    updated_user = UpdateUserStatusUseCase(user_repository).execute(inactive_user.id, False)

    assert updated_user is not None
    assert not updated_user.active
    assert ListUsersUseCase(user_repository).execute(active_only=True) == [active_user]
    assert UpdateUserStatusUseCase(user_repository).execute(uuid4(), True) is None
