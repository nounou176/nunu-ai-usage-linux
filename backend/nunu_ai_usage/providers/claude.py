import json
import os
import re
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


class ClaudeProvider(BaseProvider):
    provider_id = "claude"
    display_name = "Claude"

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

    def _find_claude_cli(self):
        candidates = [
            os.environ.get("NUNU_CLAUDE_CLI"),
            shutil.which("claude"),
        ]

        candidates.extend(
            sorted(
                Path.home().glob(
                    ".nvm/versions/node/*/bin/claude"
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
                / "claude"
                / profile_id
            )

        return Path.home() / ".claude"

    def _environment(self, account: AccountData):
        env = os.environ.copy()

        claude = self._find_claude_cli()

        if claude:
            cli_dir = str(
                Path(claude).parent
            )

            current_path = env.get(
                "PATH",
                "",
            )

            env["PATH"] = (
                cli_dir
                + os.pathsep
                + current_path
            )

        env["CLAUDE_CONFIG_DIR"] = str(
            self._profile_dir(account)
        )

        return env

    def _is_authenticated(
        self,
        account: AccountData,
    ) -> bool:

        claude = self._find_claude_cli()

        if not claude:
            return False

        try:
            result = subprocess.run(
                [
                    claude,
                    "auth",
                    "status",
                ],
                env=self._environment(account),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (
            subprocess.SubprocessError,
            OSError,
        ):
            return False

        if result.returncode != 0:
            return False

        output = (
            result.stdout
            + result.stderr
        ).strip()

        if not output:
            return False

        try:
            data = json.loads(output)

            if isinstance(data, dict):
                value = data.get(
                    "loggedIn",
                    data.get("logged_in"),
                )

                if isinstance(value, bool):
                    return value

        except json.JSONDecodeError:
            pass

        normalized = re.sub(
            r"\\s+",
            "",
            output.lower(),
        )

        return (
            "loggedin:true" in normalized
            or "\"loggedin\":true" in normalized
            or "loggedin" in normalized
            and "true" in normalized
        )

    def detect(
        self,
        account: AccountData,
    ) -> ProviderDetection:

        codexbar = self._find_codexbar()
        claude = self._find_claude_cli()

        if not codexbar:
            return ProviderDetection(
                available=False,
                authenticated=False,
                message="CodexBar CLI not found",
            )

        if not claude:
            return ProviderDetection(
                available=False,
                authenticated=False,
                message="Claude CLI not found",
            )

        authenticated = self._is_authenticated(
            account
        )

        return ProviderDetection(
            available=True,
            authenticated=authenticated,
            message=(
                "Claude connected"
                if authenticated
                else "Claude sign-in required"
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
                message="Claude is already connected",
            )

        if not self._find_claude_cli():
            return LoginStart(
                state="unavailable",
                message="Claude CLI not found",
            )

        return LoginStart(
            state="ready",
            message=(
                "Claude login will be handled "
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
                message="Claude connected",
            )

        return LoginStatus(
            state="disconnected",
            message="Claude sign-in required",
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

        if not self._find_claude_cli():
            raise RuntimeError(
                "Claude CLI not found"
            )

        result = subprocess.run(
            [
                codexbar,
                "usage",
                "--provider",
                "claude",
                "--source",
                "cli",
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
                "Claude usage fetch failed"
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
                "Claude usage record not found"
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
                "Claude returned no quota windows"
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
        # Never destroy an existing Claude login implicitly.
        # Managed-profile removal belongs to account management.
        return None
