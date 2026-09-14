from nunu_ai_usage.models import (
    UsageSnapshot,
    UsageWindow,
)


VALID_DISPLAY_MODES = {
    "left",
    "used",
}


def normalize_display_mode(mode: str | None) -> str:
    if not isinstance(mode, str):
        return "left"

    normalized = mode.strip().lower()

    if normalized not in VALID_DISPLAY_MODES:
        return "left"

    return normalized


def clamp_percent(value: float) -> float:
    return max(
        0.0,
        min(100.0, float(value)),
    )


def display_percent(
    window: UsageWindow,
    mode: str,
) -> float:

    mode = normalize_display_mode(mode)

    used = clamp_percent(
        window.used_percent
    )

    if mode == "used":
        return used

    return 100.0 - used


def display_suffix(mode: str) -> str:
    mode = normalize_display_mode(mode)

    if mode == "used":
        return "USED"

    return "LEFT"


def present_window(
    window: UsageWindow,
    mode: str,
) -> dict:

    mode = normalize_display_mode(mode)

    percent = display_percent(
        window,
        mode,
    )

    suffix = display_suffix(mode)

    return {
        "name": window.name,
        "percent": percent,
        "suffix": suffix,
        "text": (
            f"{percent:.0f}% {suffix}"
        ),
        "bar_percent": percent,
        "used_percent": clamp_percent(
            window.used_percent
        ),
        "left_percent": (
            100.0
            - clamp_percent(
                window.used_percent
            )
        ),
        "reset_at": window.reset_at,
        "reset_text": window.reset_text,
    }


def present_snapshot(
    snapshot: UsageSnapshot,
    mode: str,
) -> dict:

    mode = normalize_display_mode(mode)

    return {
        "provider": snapshot.provider,
        "account_id": snapshot.account_id,
        "display_mode": mode,
        "fetched_at": snapshot.fetched_at,
        "windows": [
            present_window(
                window,
                mode,
            )
            for window in snapshot.windows
        ],
    }
