from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    full_name: str
    role: str
    active: bool = field(default=True)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def set_active(self, active: bool) -> None:
        self.active = active
        self.updated_at = datetime.now(timezone.utc)
