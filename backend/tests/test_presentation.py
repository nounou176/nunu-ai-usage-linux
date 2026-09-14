from nunu_ai_usage.models import (
    UsageSnapshot,
    UsageWindow,
)
from nunu_ai_usage.presentation import (
    display_percent,
    display_suffix,
    normalize_display_mode,
    present_snapshot,
)


window = UsageWindow(
    name="Weekly",
    used_percent=7,
    reset_text="in 2 days",
)


assert display_percent(window, "left") == 93
assert display_suffix("left") == "LEFT"

assert display_percent(window, "used") == 7
assert display_suffix("used") == "USED"

assert normalize_display_mode(
    "something-invalid"
) == "left"


snapshot = UsageSnapshot(
    provider="demo",
    account_id="demo-account",
    windows=[
        UsageWindow(
            name="5-hour",
            used_percent=0,
        ),
        UsageWindow(
            name="Weekly",
            used_percent=7,
        ),
    ],
)


left = present_snapshot(
    snapshot,
    "left",
)

used = present_snapshot(
    snapshot,
    "used",
)


assert left["display_mode"] == "left"
assert left["windows"][0]["text"] == "100% LEFT"
assert left["windows"][0]["bar_percent"] == 100
assert left["windows"][1]["text"] == "93% LEFT"
assert left["windows"][1]["bar_percent"] == 93

assert used["display_mode"] == "used"
assert used["windows"][0]["text"] == "0% USED"
assert used["windows"][0]["bar_percent"] == 0
assert used["windows"][1]["text"] == "7% USED"
assert used["windows"][1]["bar_percent"] == 7


print("LEFT mode:")

for item in left["windows"]:
    name = item["name"]
    text = item["text"]
    bar = item["bar_percent"]

    print(
        f"  {name:10} "
        f"{text:10} "
        f"bar={bar:.0f}%"
    )


print()
print("USED mode:")

for item in used["windows"]:
    name = item["name"]
    text = item["text"]
    bar = item["bar_percent"]

    print(
        f"  {name:10} "
        f"{text:10} "
        f"bar={bar:.0f}%"
    )


print()
print("LEFT / USED engine: OK")
