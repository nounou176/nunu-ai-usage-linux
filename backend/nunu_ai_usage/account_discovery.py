from nunu_ai_usage.providers.codex import CodexProvider
from nunu_ai_usage.providers.claude import ClaudeProvider

PROVIDERS = {
    "codex": ("Codex", CodexProvider),
    "claude": ("Claude", ClaudeProvider),
}

def detect_existing_account(provider_id):
    if provider_id not in PROVIDERS:
        raise KeyError(provider_id)

    name, provider_class = PROVIDERS[provider_id]

    account = {
        "id": provider_id + "-existing",
        "provider": provider_id,
        "label": "Default",
        "enabled": True,
        "show_on_widget": True,
        "connection": {
            "type": "existing",
            "profile_id": "default",
            "source": "auto",
        },
    }

    detection = provider_class().detect(account)

    return {
        "provider": provider_id,
        "name": name,
        "available": detection.available,
        "authenticated": detection.authenticated,
        "message": detection.message,
        "account": account,
    }
