import pytest

from app.modules.users.domain.services import MfaService, PasswordService, UserDomainService
from app.modules.users.domain.value_objects import UserRole


def test_normalize_email_and_phone_number() -> None:
    assert UserDomainService.normalize_email("  Jane@Example.COM ") == "jane@example.com"
    assert UserDomainService.normalize_phone_number(" +1 514 555 0101 ") == "+1 514 555 0101"
    assert UserDomainService.normalize_phone_number("") is None
    assert UserDomainService.normalize_phone_number(None) is None


def test_invalid_email_phone_and_role_raise_value_error() -> None:
    with pytest.raises(ValueError, match="Email must be valid"):
        UserDomainService.normalize_email("missing-at-symbol")

    with pytest.raises(ValueError, match="Phone number must be valid"):
        UserDomainService.normalize_phone_number("abc")

    with pytest.raises(ValueError, match="Role must be one of"):
        UserRole("manager")


def test_password_hash_can_be_verified() -> None:
    password_hash = PasswordService.hash_password("password123")

    assert PasswordService.verify_password("password123", password_hash)
    assert not PasswordService.verify_password("wrong-password", password_hash)
    assert not PasswordService.verify_password("password123", None)
    assert not PasswordService.verify_password("password123", "invalid-format")


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="Password must contain at least 8 characters"):
        PasswordService.hash_password("short")


def test_mfa_code_hash_can_be_verified() -> None:
    code_hash = MfaService.hash_code("123456")

    assert MfaService.verify_code("123456", code_hash)
    assert not MfaService.verify_code("000000", code_hash)
    assert not MfaService.verify_code("123456", "invalid-format")
