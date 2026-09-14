from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import uuid

from nunu_ai_usage.managed_accounts import create_managed_account
from nunu_ai_usage.managed_login import (
    prepare_managed_profile,
    resolve_login_profile,
)


@dataclass
class LoginSession:
    session_id: str
    provider: str
    account: dict[str, Any]
    profile: Path
    state: str = "created"
    login_url: str | None = None
    user_code: str | None = None
    process_pid: int | None = None
    message: str = ""
    started_at: str = field(
        default_factory=lambda: datetime.now().astimezone().isoformat()
    )

    def set_challenge(self, url=None, code=None):
        self.login_url = url
        self.user_code = code
        self.state = "waiting_for_user"

    def mark_authenticated(self):
        self.state = "authenticated"
        self.message = "Login verified"

    def mark_failed(self, message):
        self.state = "failed"
        self.message = str(message)

    def public_dict(self):
        return {
            "session_id": self.session_id,
            "provider": self.provider,
            "account_id": self.account["id"],
            "profile_id": self.account["connection"]["profile_id"],
            "state": self.state,
            "login_url": self.login_url,
            "user_code": self.user_code,
            "process_pid": self.process_pid,
            "message": self.message,
            "started_at": self.started_at,
        }


def create_login_session(provider_id, label="Account"):
    account = create_managed_account(provider_id, label=label)
    profile = prepare_managed_profile(account)

    return LoginSession(
        session_id=uuid.uuid4().hex,
        provider=provider_id,
        account=account,
        profile=profile,
    )


def create_reconnect_session(account):
    reconnect_account = deepcopy(account)

    profile = resolve_login_profile(
        reconnect_account
    )

    return LoginSession(
        session_id=uuid.uuid4().hex,
        provider=reconnect_account["provider"],
        account=reconnect_account,
        profile=profile,
    )
