import json
from pathlib import Path
from typing import Any


APP_DIR_NAME = "nunu-ai-usage-linux"


class AccountStore:
    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path.home() / ".config" / APP_DIR_NAME

        self.config_dir = Path(config_dir)
        self.path = self.config_dir / "config.json"

    def default_config(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "settings": {
                "display_mode": "left",
                "refresh_seconds": 60,
                "widget": {
                    "monitor": "primary",
                    "anchor": "top-right",
                    "margin_x": 32,
                    "margin_y": 32,
                    "keep_visible": True,
                },
            },
            "accounts": [],
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.default_config()

        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "NUNU config contains invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError("NUNU config must be an object")

        if not isinstance(data.get("accounts"), list):
            raise RuntimeError("NUNU accounts must be a list")

        return data

    def save(self, config: dict[str, Any]) -> None:
        self.config_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = self.path.with_suffix(".json.tmp")

        temp_path.write_text(
            json.dumps(
                config,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

        temp_path.chmod(0o600)
        temp_path.replace(self.path)
        self.path.chmod(0o600)

    def find_account(self, account_id: str) -> dict[str, Any] | None:
        config = self.load()

        for account in config["accounts"]:
            if account.get("id") == account_id:
                return account

        return None

    def add_account(self, account: dict[str, Any]) -> None:
        account_id = account.get("id")
        provider = account.get("provider")
        label = account.get("label")

        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("Account id is required")

        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("Provider is required")

        if not isinstance(label, str) or not label.strip():
            raise ValueError("Account label is required")

        config = self.load()

        for existing in config["accounts"]:
            if existing.get("id") == account_id:
                raise ValueError(
                    f"Account already exists: {account_id}"
                )

        config["accounts"].append(account)
        self.save(config)

    def rename_account(self, account_id: str, label: str) -> None:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Account label is required")

        config = self.load()

        for account in config["accounts"]:
            if account.get("id") == account_id:
                account["label"] = label.strip()
                self.save(config)
                return

        raise KeyError(f"Unknown account: {account_id}")

    def set_display_mode(
        self,
        mode: str,
    ) -> None:
        if mode not in ("left", "used"):
            raise ValueError(
                "display_mode must be left or used"
            )

        config = self.load()

        config.setdefault(
            "settings",
            {},
        )["display_mode"] = mode

        self.save(config)


    def set_refresh_seconds(
        self,
        seconds: int,
    ) -> None:
        if isinstance(seconds, bool):
            raise ValueError(
                "refresh_seconds must be an integer"
            )

        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            raise ValueError(
                "refresh_seconds must be an integer"
            )

        if seconds <= 0:
            raise ValueError(
                "refresh_seconds must be greater than zero"
            )

        config = self.load()

        config.setdefault(
            "settings",
            {},
        )["refresh_seconds"] = seconds

        self.save(config)


    def set_account_visibility(
        self,
        account_id,
        visible,
    ):
        config = self.load()
        account = None

        for item in config["accounts"]:
            if item["id"] == account_id:
                account = item
                break

        if account is None:
            raise KeyError(
                "Account not found: " + account_id
            )

        account["show_on_widget"] = bool(visible)

        self.save(config)

        return account


    def remove_account(self, account_id: str) -> dict[str, Any]:
        config = self.load()

        for index, account in enumerate(config["accounts"]):
            if account.get("id") == account_id:
                removed = config["accounts"].pop(index)
                self.save(config)
                return removed

        raise KeyError(f"Unknown account: {account_id}")
