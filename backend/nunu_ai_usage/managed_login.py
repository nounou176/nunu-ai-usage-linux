import os
import shutil
from pathlib import Path


DATA_ROOT = Path.home() / ".local" / "share" / "nunu-ai-usage-linux"


def find_cli(name):
    path = shutil.which(name)

    if path:
        return path

    matches = sorted(
        Path.home().glob(
            ".nvm/versions/node/*/bin/" + name
        ),
        reverse=True,
    )

    for candidate in matches:
        if candidate.is_file():
            return str(candidate)

    return None


def managed_profile_dir(account):
    provider = account["provider"]
    profile_id = account["connection"]["profile_id"]

    return DATA_ROOT / "profiles" / provider / profile_id


def prepare_managed_profile(account):
    path = managed_profile_dir(account)
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


def native_profile_dir(provider):
    if provider == "codex":
        return Path.home() / ".codex"

    if provider == "claude":
        return Path.home() / ".claude"

    raise KeyError(provider)


def resolve_login_profile(account):
    connection = account.get("connection", {})

    if connection.get("type") == "existing":
        return native_profile_dir(
            account["provider"]
        )

    return prepare_managed_profile(account)


def build_login(account):
    provider = account["provider"]
    profile = resolve_login_profile(account)
    env = os.environ.copy()

    if provider == "codex":
        binary = find_cli("codex")
        if not binary:
            raise RuntimeError("Codex CLI not found")
        env["PATH"] = str(Path(binary).parent) + os.pathsep + env.get("PATH", "")
        env["CODEX_HOME"] = str(profile)
        command = [binary, "login", "--device-auth"]

    elif provider == "claude":
        binary = find_cli("claude")
        if not binary:
            raise RuntimeError("Claude CLI not found")
        env["PATH"] = str(Path(binary).parent) + os.pathsep + env.get("PATH", "")
        env["CLAUDE_CONFIG_DIR"] = str(profile)
        command = [binary, "auth", "login", "--claudeai"]

    else:
        raise KeyError(provider)

    return command, env, profile
