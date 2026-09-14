import json
import os
import shutil
import subprocess
from pathlib import Path

from nunu_ai_usage.models import (
    AccountData,
    LoginStart,
    LoginStatus,
    ProviderDetection,
    UsageSnapshot,
    UsageWindow,
)
from nunu_ai_usage.providers.base import BaseProvider


class CodexProvider(BaseProvider):
    provider_id = "codex"
    display_name = "Codex"

    def _find_executable(self, candidates):
        for candidate in candidates:
            if not candidate:
                continue

            path = Path(candidate).expanduser()

            if path.is_file() and os.access(path, os.X_OK):
                return str(path)

        return None

    def _find_codexbar(self):
        candidates = [
            os.environ.get("NUNU_CODEXBAR_PATH"),
            shutil.which("codexbar"),
            shutil.which("CodexBarCLI"),
            Path.home()
            / ".local"
            / "opt"
            / "codexbar"
            / "CodexBarCLI",
        ]

        return self._find_executable(candidates)

    def _find_codex_cli(self):
        candidates = [
            os.environ.get("NUNU_CODEX_CLI"),
            shutil.which("codex"),
        ]

        candidates.extend(
            sorted(
                Path.home().glob(
                    ".nvm/versions/node/*/bin/codex"
                ),
                reverse=True,
            )
        )

        return self._find_executable(candidates)

    def _profile_dir(self, account: AccountData) -> Path:
        connection = account.get("connection", {})

        explicit = connection.get("profile_dir")

        if explicit:
            return Path(explicit).expanduser()

        connection_type = connection.get(
            "type",
            "existing",
        )

        if connection_type == "managed":
            profile_id = connection.get(
                "profile_id",
                account["id"],
            )

            root = (
                self.runtime_dir
                if self.runtime_dir is not None
                else (
                    Path.home()
                    / ".local"
                    / "share"
                    / "nunu-ai-usage-linux"
                )
            )

            return (
                Path(root)
                / "profiles"
                / "codex"
                / profile_id
            )

        return Path.home() / ".codex"

    def _environment(self, account: AccountData):
        env = os.environ.copy()
        env["CODEX_HOME"] = str(
            self._profile_dir(account)
        )
        return env

    def detect(
        self,
        account: AccountData,
    ) -> ProviderDetection:

        codexbar = self._find_codexbar()

        if not codexbar:
            return ProviderDetection(
                available=False,
                authenticated=False,
                message="CodexBar CLI not found",
            )

        profile_dir = self._profile_dir(account)
        codex_cli = self._find_codex_cli()

        authenticated = False

        if codex_cli:
            try:
                result = subprocess.run(
                    [
                        codex_cli,
                        "login",
                        "status",
                    ],
                    env=self._environment(account),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                output = (
                    result.stdout
                    + result.stderr
                ).lower()

                authenticated = (
                    result.returncode == 0
                    and "logged in" in output
                )

            except (
                subprocess.SubprocessError,
                OSError,
            ):
                authenticated = False

        else:
            authenticated = (
                profile_dir / "auth.json"
            ).is_file()

        return ProviderDetection(
            available=True,
            authenticated=authenticated,
            message=(
                "Codex connected"
                if authenticated
                else "Codex sign-in required"
            ),
        )

    def begin_login(
        self,
        account: AccountData,
    ) -> LoginStart:

        detection = self.detect(account)

        if detection.authenticated:
            return LoginStart(
                state="connected",
                message="Codex is already connected",
            )

        if not self._find_codex_cli():
            return LoginStart(
                state="unavailable",
                message="Codex CLI not found",
            )

        return LoginStart(
            state="ready",
            message=(
                "Codex login will be handled "
                "by the Add Account wizard"
            ),
        )

    def check_login(
        self,
        account: AccountData,
    ) -> LoginStatus:

        detection = self.detect(account)

        if not detection.available:
            return LoginStatus(
                state="unavailable",
                message=detection.message,
            )

        if detection.authenticated:
            return LoginStatus(
                state="connected",
                message="Codex connected",
            )

        return LoginStatus(
            state="disconnected",
            message="Codex sign-in required",
        )

    def _find_usage_record(self, value):
        if isinstance(value, dict):
            usage = value.get("usage")

            if isinstance(usage, dict) and (
                "primary" in usage
                or "secondary" in usage
            ):
                return value

            for child in value.values():
                found = self._find_usage_record(
                    child
                )

                if found:
                    return found

        elif isinstance(value, list):
            for child in value:
                found = self._find_usage_record(
                    child
                )

                if found:
                    return found

        return None

    def _window_name(
        self,
        key,
        window,
    ):
        minutes = window.get("windowMinutes")

        if minutes == 300:
            return "5-hour"

        if minutes == 10080:
            return "Weekly"

        if minutes == 1440:
            return "Daily"

        if key == "primary":
            return "Session"

        if key == "secondary":
            return "Secondary"

        return key.replace("_", " ").title()

    def fetch_usage(
        self,
        account: AccountData,
    ) -> UsageSnapshot:

        codexbar = self._find_codexbar()

        if not codexbar:
            raise RuntimeError(
                "CodexBar CLI not found"
            )

        result = subprocess.run(
            [
                codexbar,
                "usage",
                "--provider",
                "codex",
                "--source",
                "oauth",
                "--format",
                "json",
            ],
            env=self._environment(account),
            capture_output=True,
            text=True,
            timeout=90,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Codex usage fetch failed"
            )

        try:
            payload = json.loads(
                result.stdout
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "CodexBar returned invalid JSON"
            ) from exc

        record = self._find_usage_record(
            payload
        )

        if not record:
            raise RuntimeError(
                "Codex usage record not found"
            )

        usage = record["usage"]
        windows = []

        for key in (
            "primary",
            "secondary",
            "tertiary",
        ):
            window = usage.get(key)

            if not isinstance(window, dict):
                continue

            used = window.get(
                "usedPercent"
            )

            if used is None:
                continue

            used = max(
                0.0,
                min(100.0, float(used)),
            )

            windows.append(
                UsageWindow(
                    name=self._window_name(
                        key,
                        window,
                    ),
                    used_percent=used,
                    reset_at=(
                        window.get("resetsAt")
                        or window.get("resetAt")
                    ),
                    reset_text=window.get(
                        "resetDescription"
                    ),
                )
            )

        if not windows:
            raise RuntimeError(
                "Codex returned no quota windows"
            )

        return UsageSnapshot(
            provider=self.provider_id,
            account_id=account["id"],
            windows=windows,
        )

    def disconnect(
        self,
        account: AccountData,
    ) -> None:
        # Authentication removal will be implemented
        # by the account-management UX.
        #
        # Never modify an existing Codex profile
        # implicitly.
        return None
