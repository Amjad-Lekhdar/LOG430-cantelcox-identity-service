import hashlib
import hmac
import secrets

from app.modules.users.domain.entities import User


class UserDomainService:
    @staticmethod
    def normalize_email(email: str) -> str:
        normalized_email = email.strip().lower()
        if "@" not in normalized_email:
            raise ValueError("Email must be valid")
        return normalized_email

    @staticmethod
    def ensure_email_is_available(existing_user: User | None, email: str) -> None:
        if existing_user is not None:
            raise ValueError(f"User with email {email} already exists")


class PasswordService:
    _iterations = 600_000

    @staticmethod
    def hash_password(password: str) -> str:
        PasswordService._validate_password(password)
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PasswordService._iterations,
        ).hex()
        return f"pbkdf2_sha256${PasswordService._iterations}${salt}${password_hash}"

    @staticmethod
    def verify_password(password: str, stored_password_hash: str | None) -> bool:
        if stored_password_hash is None:
            return False
        try:
            algorithm, iterations, salt, expected_hash = stored_password_hash.split("$", 3)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")
