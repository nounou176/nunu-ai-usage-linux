from abc import ABC, abstractmethod
from pathlib import Path

from nunu_ai_usage.models import (
    AccountData,
    LoginStart,
    LoginStatus,
    ProviderDetection,
    UsageSnapshot,
)


class BaseProvider(ABC):
    provider_id: str = ""
    display_name: str = ""

    def __init__(self, runtime_dir: Path | None = None):
        self.runtime_dir = runtime_dir

    @abstractmethod
    def detect(self, account: AccountData) -> ProviderDetection:
        raise NotImplementedError

    @abstractmethod
    def begin_login(self, account: AccountData) -> LoginStart:
        raise NotImplementedError

    @abstractmethod
    def check_login(self, account: AccountData) -> LoginStatus:
        raise NotImplementedError

    @abstractmethod
    def fetch_usage(self, account: AccountData) -> UsageSnapshot:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self, account: AccountData) -> None:
        raise NotImplementedError
