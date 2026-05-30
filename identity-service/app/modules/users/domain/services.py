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
