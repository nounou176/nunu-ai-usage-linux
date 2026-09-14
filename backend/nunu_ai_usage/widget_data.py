from contextlib import contextmanager
from datetime import datetime
import os

from nunu_ai_usage.account_store import AccountStore
from nunu_ai_usage.providers.codex import CodexProvider
from nunu_ai_usage.providers.claude import ClaudeProvider


PROVIDERS = {
    "codex": ("Codex", CodexProvider),
    "claude": ("Claude", ClaudeProvider),
}


@contextmanager
def _noninteractive_environment():
    overrides = {
        "BROWSER": "/bin/false",
        "CI": "1",
        "NO_COLOR": "1",
    }

    previous = {
        key: os.environ.get(key)
        for key in overrides
    }

    try:
        os.environ.update(overrides)
        yield

    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _clamp(value):
    value = float(value)
    return max(0.0, min(100.0, value))


def _window_data(window, mode):
    used = _clamp(window.used_percent)
    left = _clamp(window.left_percent)

    percent = (
        left
        if mode == "left"
        else used
    )

    return {
        "name": window.name,
        "used_percent": round(used),
        "left_percent": round(left),
        "display_percent": round(percent),
        "display_suffix": mode.upper(),
        "reset_text": (
            window.reset_text
            or window.reset_at
            or None
        ),
    }


def build_widget_data(store=None):
    if store is None:
        store = AccountStore()

    config = store.load()

    settings = config.get(
        "settings",
        {},
    )

    mode = settings.get(
        "display_mode",
        "left",
    )

    if mode not in ("left", "used"):
        mode = "left"

    try:
        refresh_seconds = int(
            settings.get(
                "refresh_seconds",
                60,
            )
        )
    except (TypeError, ValueError):
        refresh_seconds = 60

    refresh_seconds = max(
        1,
        refresh_seconds,
    )

    result = {
        "schema_version": 1,
        "display_mode": mode,
        "refresh_seconds": refresh_seconds,
        "generated_at": (
            datetime.now()
            .astimezone()
            .isoformat()
        ),
        "accounts": [],
    }

    for account in config.get(
        "accounts",
        [],
    ):
        if not account.get(
            "enabled",
            True,
        ):
            continue

        if not account.get(
            "show_on_widget",
            True,
        ):
            continue

        provider_id = account.get(
            "provider"
        )

        provider_info = PROVIDERS.get(
            provider_id
        )

        if provider_info is None:
            continue

        provider_name, provider_class = (
            provider_info
        )

        item = {
            "provider": provider_id,
            "provider_name": provider_name,
            "label": account.get(
                "label",
                "Account",
            ),
            "ok": False,
            "windows": [],
        }

        try:
            provider = provider_class()

            with _noninteractive_environment():
                detection = provider.detect(
                    account
                )

                if (
                    not detection.available
                    or not detection.authenticated
                ):
                    item["message"] = (
                        detection.message
                        or "Usage unavailable"
                    )

                    result["accounts"].append(
                        item
                    )

                    continue

                snapshot = provider.fetch_usage(
                    account
                )

            item["windows"] = [
                _window_data(
                    window,
                    mode,
                )
                for window in snapshot.windows
            ]

            item["ok"] = True

        except Exception:
            item["message"] = (
                "Usage unavailable"
            )

        result["accounts"].append(
            item
        )

    return result
