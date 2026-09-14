from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProviderDetection:
    available: bool
    authenticated: bool = False
    message: str = ""


@dataclass
class LoginStart:
    state: str
    url: str | None = None
    user_code: str | None = None
    message: str = ""


@dataclass
class LoginStatus:
    state: str
    message: str = ""


@dataclass
class UsageWindow:
    name: str
    used_percent: float
    reset_at: str | None = None
    reset_text: str | None = None

    @property
    def left_percent(self) -> float:
        return max(0.0, min(100.0, 100.0 - self.used_percent))


@dataclass
class UsageSnapshot:
    provider: str
    account_id: str
    windows: list[UsageWindow] = field(default_factory=list)
    fetched_at: str = field(
        default_factory=lambda: datetime.now().astimezone().isoformat()
    )


AccountData = dict[str, Any]
