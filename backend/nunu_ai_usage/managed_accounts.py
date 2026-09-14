import uuid


def create_managed_account(provider_id, label=None):
    if provider_id not in ("codex", "claude"):
        raise KeyError(provider_id)

    short_id = uuid.uuid4().hex[:8]
    profile_id = provider_id + "-" + short_id

    if label is None:
        label = "Account"

    return {
        "id": profile_id,
        "provider": provider_id,
        "label": label,
        "enabled": True,
        "show_on_widget": True,
        "connection": {
            "type": "managed",
            "profile_id": profile_id,
            "source": "auto",
        },
    }
