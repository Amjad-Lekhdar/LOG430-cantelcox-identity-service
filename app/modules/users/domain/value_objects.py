from dataclasses import dataclass


@dataclass(frozen=True)
class UserRole:
    value: str

    def __post_init__(self) -> None:
        allowed_roles = {"admin", "agent", "customer"}
        if self.value not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed_roles))}")
