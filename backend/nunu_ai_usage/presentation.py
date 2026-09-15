import re

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


def normalize_reset_text(
    value: str | None,
) -> str | None:
    if not isinstance(value, str):
        return value

    text = value.strip()

    if not text:
        return text

    # Some providers include their own "Resets" prefix.
    # Presentation consumers add that label themselves.
    text = re.sub(
        r"^resets\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove provider timezone suffixes such as:
    #   (Asia/Ho_Chi_Minh)
    text = re.sub(
        r"\s*\([A-Za-z_]+(?:/[A-Za-z_+-]+)+\)\s*$",
        "",
        text,
    )

    # Sep16 -> Sep 16
    text = re.sub(
        r"\b([A-Za-z]{3})(\d{1,2})\b",
        r"\1 \2",
        text,
    )

    # Sep 16,12pm -> Sep 16, 12pm
    text = re.sub(
        r",\s*",
        ", ",
        text,
    )

    # 5:50pm -> 5:50 PM
    # 12pm    -> 12 PM
    text = re.sub(
        r"(?i)\s*(am|pm)\b",
        lambda match: " " + match.group(1).upper(),
        text,
    )

    return text.strip()


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
        "reset_text": normalize_reset_text(
            window.reset_text
        ),
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
