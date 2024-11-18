from enum import Enum
from datetime import datetime

class APIType(Enum):
    ETHERSCAN = 1
    GITLAB = 2
    ANTHROPIC = 3
    # ... add other API types

class APICredential:
    def __init__(self, name: str, api_type: APIType, key: str, endpoint: str = "", rate_limit: int = 0, is_valid: bool = False, created_at: datetime = None, last_used: datetime = None):
        self.name = name
        self.api_type = api_type
        self.key = key
        self.endpoint = endpoint
        self.rate_limit = rate_limit
        self.is_valid = is_valid
        self.created_at = created_at or datetime.now()
        self.last_used = last_used

    def to_dict(self):
        return {
            "name": self.name,
            "api_type": self.api_type.name,  # Store as string
            "key": self.key,
            "endpoint": self.endpoint,
            "rate_limit": self.rate_limit,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat(),  # Store as ISO string
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    @staticmethod
    def from_dict(data):
        return APICredential(
            name=data["name"],
            api_type=APIType[data["api_type"]],  # Convert back to Enum
            key=data["key"],
            endpoint=data["endpoint"],
            rate_limit=data["rate_limit"],
            is_valid=data["is_valid"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data["last_used"] else None,
        )


class APIValidationError(Exception):
    pass




"""Data models for API management system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional

class APIType(Enum):
    """Supported API types."""
    ETHERSCAN = auto()
    GITLAB = auto()
    ANTHROPIC = auto()
    SNAPSHOT = auto()
    CUSTOM = auto()

@dataclass
class APICredential:
    """Container for API credential information."""
    name: str
    key: str
    api_type: APIType
    endpoint: Optional[str] = None
    rate_limit: int = 0
    created_at: datetime = None
    last_used: datetime = None
    is_valid: bool = False
    notes: str = ""

    def __post_init__(self):
        """Set default timestamps if not provided."""
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.last_used:
            self.last_used = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['api_type'] = self.api_type.name
        data['created_at'] = self.created_at.isoformat()
        data['last_used'] = self.last_used.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'APICredential':
        """Create instance from dictionary."""
        data['api_type'] = APIType[data['api_type']]
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_used'] = datetime.fromisoformat(data['last_used'])
        return cls(**data)

class APIValidationError(Exception):
    """Raised when API credential validation fails."""
    pass