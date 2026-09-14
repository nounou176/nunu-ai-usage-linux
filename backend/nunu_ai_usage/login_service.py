from copy import deepcopy

from nunu_ai_usage.account_store import AccountStore
from nunu_ai_usage.providers.codex import CodexProvider
from nunu_ai_usage.providers.claude import ClaudeProvider


PROVIDERS = {
    "codex": CodexProvider,
    "claude": ClaudeProvider,
}


def verify_login_session(session):
    provider_class = PROVIDERS.get(session.provider)

    if provider_class is None:
        return False, "Unsupported provider"

    account = deepcopy(session.account)

    connection = dict(account.get("connection", {}))
    connection["profile_dir"] = str(session.profile)
    account["connection"] = connection

    provider = provider_class()
    result = provider.detect(account)

    if not result.available:
        return False, result.message

    if not result.authenticated:
        return False, result.message

    session.mark_authenticated()

    return True, result.message


def save_login_session(session, store=None):
    if session.state != "authenticated":
        raise RuntimeError("Login session is not verified")

    if store is None:
        store = AccountStore()

    clean = deepcopy(session.account)

    connection = dict(clean.get("connection", {}))
    connection.pop("profile_dir", None)
    clean["connection"] = connection

    existing = store.find_account(clean["id"])

    if existing is not None:
        return existing, False

    store.add_account(clean)

    return clean, True
