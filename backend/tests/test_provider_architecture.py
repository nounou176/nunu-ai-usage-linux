from nunu_ai_usage.models import (
    LoginStart,
    LoginStatus,
    ProviderDetection,
    UsageSnapshot,
    UsageWindow,
)
from nunu_ai_usage.providers.base import BaseProvider
from nunu_ai_usage.providers.registry import (
    create_provider,
    list_providers,
    register_provider,
)


class DemoProvider(BaseProvider):
    provider_id = "demo"
    display_name = "Demo AI"

    def detect(self, account):
        return ProviderDetection(
            available=True,
            authenticated=True,
        )

    def begin_login(self, account):
        return LoginStart(state="connected")

    def check_login(self, account):
        return LoginStatus(state="connected")

    def fetch_usage(self, account):
        return UsageSnapshot(
            provider=self.provider_id,
            account_id=account["id"],
            windows=[
                UsageWindow(
                    name="Session",
                    used_percent=25.0,
                    reset_text="in 2 hours",
                ),
                UsageWindow(
                    name="Weekly",
                    used_percent=40.0,
                    reset_text="in 3 days",
                ),
            ],
        )

    def disconnect(self, account):
        return None


register_provider(DemoProvider)

assert list_providers() == ["demo"]

provider = create_provider("demo")

account = {
    "id": "demo-personal",
    "provider": "demo",
    "label": "Personal",
}

detection = provider.detect(account)
assert detection.available is True
assert detection.authenticated is True

snapshot = provider.fetch_usage(account)

assert snapshot.windows[0].used_percent == 25.0
assert snapshot.windows[0].left_percent == 75.0
assert snapshot.windows[1].used_percent == 40.0
assert snapshot.windows[1].left_percent == 60.0

print("Provider architecture: OK")
print("Registered:", ", ".join(list_providers()))

for window in snapshot.windows:
    print(
        f"{window.name}: "
        f"{window.used_percent:.0f}% USED / "
        f"{window.left_percent:.0f}% LEFT"
    )
