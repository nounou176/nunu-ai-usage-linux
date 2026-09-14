from nunu_ai_usage.account_discovery import detect_existing_account
from nunu_ai_usage.account_store import AccountStore


def use_existing_account(provider_id, store=None):
    if store is None:
        store = AccountStore()

    result = detect_existing_account(provider_id)

    if not result["available"]:
        raise RuntimeError(result["message"])

    if not result["authenticated"]:
        raise RuntimeError(result["message"])

    account = result["account"]
    account_id = account["id"]

    existing = store.find_account(account_id)

    if existing is not None:
        return existing, False

    store.add_account(account)
    return account, True
