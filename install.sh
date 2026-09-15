#!/bin/sh

# NUNU AI Usage Linux
# Per-user installer for Linux Mint Cinnamon, Xfce, MATE, and compatible X11 desktops.
#
# This installer:
# - does not require sudo
# - does not copy provider credentials
# - preserves existing NUNU config and managed profiles
# - reuses an existing CodexBarCLI when available
# - downloads CodexBarCLI only when missing
# - verifies the published SHA-256 before installing CodexBar

set -u

APP_ID="nunu-ai-usage-linux"
DESKLET_UUID="nunu-ai-usage-linux@nunu"

SCRIPT_DIR=$(
    CDPATH= cd -- "$(dirname -- "$0")" &&
    pwd
)

DATA_ROOT="$HOME/.local/share/$APP_ID"
APP_ROOT="$DATA_ROOT/app"
APP_NEW="$DATA_ROOT/app.new"

PROFILE_ROOT="$DATA_ROOT/profiles"

CONFIG_ROOT="$HOME/.config/$APP_ID"
CONFIG_FILE="$CONFIG_ROOT/config.json"

BIN_ROOT="$HOME/.local/bin"

DESKLET_ROOT="$HOME/.local/share/cinnamon/desklets"
DESKLET_DEST="$DESKLET_ROOT/$DESKLET_UUID"
DESKLET_NEW="$DESKLET_ROOT/$DESKLET_UUID.new"

CODEXBAR_ROOT="$HOME/.local/opt/codexbar"
CODEXBAR_BIN="$CODEXBAR_ROOT/CodexBarCLI"

INSTALL_CODEXBAR=1
ENABLE_DESKLET=1

DESKTOP_KIND="other"
INSTALL_DESKLET=0
INSTALL_AUTOSTART=1

AUTOSTART_ROOT="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_ROOT/nunu-ai-usage-widget.desktop"

APPLICATIONS_ROOT="$HOME/.local/share/applications"
APPLICATION_FILE="$APPLICATIONS_ROOT/nunu-ai-usage.desktop"


say() {
    printf '%s\n' "$*"
}


die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}


usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --skip-codexbar   Do not install CodexBarCLI when missing.
  --no-enable       Do not automatically enable the Cinnamon Desklet.
  -h, --help        Show this help.
EOF
}


while [ "$#" -gt 0 ]; do
    case "$1" in
        --skip-codexbar)
            INSTALL_CODEXBAR=0
            ;;
        --no-enable)
            ENABLE_DESKLET=0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac

    shift
done


detect_desktop() {
    desktop_name="${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-unknown}}"

    case "$desktop_name" in
        *Cinnamon*|*cinnamon*)
            DESKTOP_KIND="cinnamon"
            INSTALL_DESKLET=1
            INSTALL_AUTOSTART=0
            ;;
        *XFCE*|*Xfce*|*xfce*)
            DESKTOP_KIND="xfce"
            INSTALL_DESKLET=0
            INSTALL_AUTOSTART=1
            ;;
        *MATE*|*Mate*|*mate*)
            DESKTOP_KIND="mate"
            INSTALL_DESKLET=0
            INSTALL_AUTOSTART=1
            ;;
        *)
            DESKTOP_KIND="other"
            INSTALL_DESKLET=0
            INSTALL_AUTOSTART=1
            ;;
    esac

    say "Detected desktop:"
    say "  $desktop_name -> $DESKTOP_KIND"
}


require_command() {
    command -v "$1" >/dev/null 2>&1 ||
        die "Required command not found: $1"
}


check_runtime_dependencies() {
    for cmd in \
        python3 \
        install \
        cp \
        rm \
        mkdir \
        mv \
        chmod \
        uname \
        xrandr
    do
        require_command "$cmd"
    done

    if [ "$INSTALL_DESKLET" -eq 1 ]; then
        require_command gsettings
    fi

    python3 - <<'PY' >/dev/null 2>&1
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk
PY

    if [ "$?" -ne 0 ]; then
        die "Python GTK3 bindings are missing (python3-gi / GTK 3)."
    fi

    if [ ! -d "$SCRIPT_DIR/backend/nunu_ai_usage" ]; then
        die "backend/nunu_ai_usage not found beside install.sh"
    fi

    if [ ! -f "$SCRIPT_DIR/gui/account_manager.py" ]; then
        die "gui/account_manager.py not found beside install.sh"
    fi

    if [ ! -f "$SCRIPT_DIR/gui/floating_widget.py" ]; then
        die "gui/floating_widget.py not found beside install.sh"
    fi

    if [ "$INSTALL_DESKLET" -eq 1 ]; then
        if [ ! -f \
            "$SCRIPT_DIR/desklet/$DESKLET_UUID/desklet.js" \
        ]; then
            die "Desklet source not found beside install.sh"
        fi
    fi
}


install_app_files() {
    say "Installing NUNU application files..."

    install -d -m 700 "$DATA_ROOT"
    install -d -m 700 "$PROFILE_ROOT"

    rm -rf "$APP_NEW"

    python3 - "$SCRIPT_DIR" "$APP_NEW" <<'PY'
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

ignore = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.before-*",
    ".pytest_cache",
)

target.mkdir(
    parents=True,
    exist_ok=False,
)

(target / "backend").mkdir(
    parents=True,
    exist_ok=True,
)

shutil.copytree(
    source / "backend" / "nunu_ai_usage",
    target / "backend" / "nunu_ai_usage",
    ignore=ignore,
)

shutil.copytree(
    source / "gui",
    target / "gui",
    ignore=ignore,
)

# Production payload must not contain local development
# backups, bytecode caches, or repository-only artifacts.
for candidate in list(target.rglob("*")):
    if not candidate.is_file():
        continue

    name = candidate.name

    if (
        ".before" in name
        or name.endswith(".bak")
        or name.endswith(".backup")
        or name.endswith(".pyc")
        or name.endswith(".pyo")
    ):
        candidate.unlink()

for cache_dir in sorted(
    target.rglob("__pycache__"),
    key=lambda item: len(item.parts),
    reverse=True,
):
    if cache_dir.is_dir():
        shutil.rmtree(
            cache_dir,
            ignore_errors=True,
        )

tests_dir = target / "backend" / "tests"

if tests_dir.exists():
    shutil.rmtree(
        tests_dir,
        ignore_errors=True,
    )
PY

    if [ "$?" -ne 0 ]; then
        rm -rf "$APP_NEW"
        die "Could not stage application files"
    fi

    rm -rf "$APP_ROOT"
    mv "$APP_NEW" "$APP_ROOT"

    chmod 700 "$DATA_ROOT"
    chmod 700 "$PROFILE_ROOT"
}


install_config() {
    say "Checking NUNU config..."

    install -d -m 700 "$CONFIG_ROOT"

    if [ -f "$CONFIG_FILE" ]; then
        chmod 600 "$CONFIG_FILE"

        say "Keeping existing config:"
        say "  $CONFIG_FILE"

        return
    fi

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$APP_ROOT/backend" \
    python3 - <<'PY'
from nunu_ai_usage.account_store import AccountStore

store = AccountStore()
store.save(
    store.default_config()
)
PY

    if [ "$?" -ne 0 ]; then
        die "Could not create initial NUNU config"
    fi

    chmod 600 "$CONFIG_FILE"

    say "Created:"
    say "  $CONFIG_FILE"
}


install_launchers() {
    say "Installing production launchers..."

    install -d -m 755 "$BIN_ROOT"

    BACKEND_TMP="$BIN_ROOT/.nunu-ai-usage.tmp"
    SETTINGS_TMP="$BIN_ROOT/.nunu-ai-usage-settings.tmp"
    WIDGET_TMP="$BIN_ROOT/.nunu-ai-usage-widget.tmp"

    cat > "$BACKEND_TMP" <<'EOF'
#!/bin/sh

APP="$HOME/.local/share/nunu-ai-usage-linux/app"

if [ "$#" -eq 0 ]; then
    set -- widget-data
fi

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$APP/backend" \
exec python3 -m nunu_ai_usage.cli "$@"
EOF

    cat > "$SETTINGS_TMP" <<'EOF'
#!/bin/sh

APP="$HOME/.local/share/nunu-ai-usage-linux/app"

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$APP/backend" \
exec python3 "$APP/gui/account_manager.py" "$@"
EOF

    cat > "$WIDGET_TMP" <<'EOF'
#!/bin/sh

APP="$HOME/.local/share/nunu-ai-usage-linux/app"

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$APP/backend" \
exec python3 "$APP/gui/floating_widget.py" "$@" </dev/null
EOF

    chmod 755 \
        "$BACKEND_TMP" \
        "$SETTINGS_TMP" \
        "$WIDGET_TMP"

    mv \
        "$BACKEND_TMP" \
        "$BIN_ROOT/nunu-ai-usage"

    mv \
        "$SETTINGS_TMP" \
        "$BIN_ROOT/nunu-ai-usage-settings"

    mv \
        "$WIDGET_TMP" \
        "$BIN_ROOT/nunu-ai-usage-widget"
}


install_desklet() {
    if [ "$INSTALL_DESKLET" -eq 0 ]; then
        say "Skipping Cinnamon Desklet on $DESKTOP_KIND."
        return
    fi

    say "Installing Cinnamon Desklet..."

    install -d -m 755 "$DESKLET_ROOT"

    rm -rf "$DESKLET_NEW"
    install -d -m 755 "$DESKLET_NEW"

    for name in \
        metadata.json \
        desklet.js \
        stylesheet.css
    do
        src="$SCRIPT_DIR/desklet/$DESKLET_UUID/$name"

        [ -f "$src" ] ||
            die "Missing Desklet file: $name"

        install -m 644 \
            "$src" \
            "$DESKLET_NEW/$name"
    done

    rm -rf "$DESKLET_DEST"
    mv "$DESKLET_NEW" "$DESKLET_DEST"
}


install_application_launcher() {
    say "Installing application menu launcher..."

    install -d -m 755 "$APPLICATIONS_ROOT"

    APPLICATION_TMP="$APPLICATIONS_ROOT/.nunu-ai-usage.desktop.tmp"

    cat > "$APPLICATION_TMP" <<EOF
[Desktop Entry]
Type=Application
Name=NUNU AI Usage
Comment=Monitor Codex and Claude usage quotas
Exec=$BIN_ROOT/nunu-ai-usage-widget
Icon=utilities-system-monitor
Terminal=false
StartupNotify=false
Categories=Utility;System;
Keywords=AI;Codex;Claude;Usage;Quota;
EOF

    chmod 644 "$APPLICATION_TMP"

    mv \
        "$APPLICATION_TMP" \
        "$APPLICATION_FILE"

    say "Application menu launcher installed:"
    say "  $APPLICATION_FILE"
}



widget_autostart_enabled() {
    python3 - <<'PYCONFIG'
import json
from pathlib import Path

path = (
    Path.home()
    / ".config"
    / "nunu-ai-usage-linux"
    / "config.json"
)

enabled = True

try:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    enabled = bool(
        data.get(
            "settings",
            {},
        ).get(
            "widget",
            {},
        ).get(
            "autostart",
            True,
        )
    )
except Exception:
    enabled = True

print("1" if enabled else "0")
PYCONFIG
}


install_autostart() {
    if [ "$INSTALL_AUTOSTART" -eq 0 ]; then
        if [ -f "$AUTOSTART_FILE" ]; then
            rm -f "$AUTOSTART_FILE"
            say "Removed floating-widget autostart for Cinnamon:"
            say "  $AUTOSTART_FILE"
        else
            say "Floating-widget autostart is not needed on Cinnamon."
        fi

        return
    fi

    if [ "$(widget_autostart_enabled)" != "1" ]; then
        rm -f "$AUTOSTART_FILE"

        say "Floating-widget autostart disabled in settings."

        return
    fi

    say "Installing desktop autostart..."

    install -d -m 700 "$AUTOSTART_ROOT"

    AUTOSTART_TMP="$AUTOSTART_ROOT/.nunu-ai-usage-widget.desktop.tmp"

    cat > "$AUTOSTART_TMP" <<EOF
[Desktop Entry]
Type=Application
Name=NUNU AI Usage
Comment=Monitor Codex and Claude usage quotas
Exec=$BIN_ROOT/nunu-ai-usage-widget
Terminal=false
Hidden=false
StartupNotify=false
EOF

    chmod 644 "$AUTOSTART_TMP"

    mv \
        "$AUTOSTART_TMP" \
        "$AUTOSTART_FILE"

    say "Floating widget will start automatically after login:"
    say "  $AUTOSTART_FILE"
}


codexbar_asset_arch() {
    case "$(uname -m)" in
        x86_64|amd64)
            printf '%s\n' "x86_64"
            ;;
        aarch64|arm64)
            printf '%s\n' "aarch64"
            ;;
        *)
            return 1
            ;;
    esac
}


install_codexbar_if_needed() {
    if [ -x "$CODEXBAR_BIN" ]; then
        say "Using existing CodexBarCLI:"
        say "  $CODEXBAR_BIN"
        return
    fi

    if [ "$INSTALL_CODEXBAR" -eq 0 ]; then
        say "CodexBarCLI is missing; download skipped."
        return
    fi

    require_command curl
    require_command tar
    require_command sha256sum
    require_command mktemp
    require_command find
    require_command sed
    require_command awk

    arch=$(codexbar_asset_arch) ||
        die "Unsupported CodexBar architecture: $(uname -m)"

    say "CodexBarCLI not found."
    say "Fetching latest official Linux release metadata..."

    tmp=$(
        mktemp -d "${TMPDIR:-/tmp}/nunu-codexbar.XXXXXX"
    ) || die "Could not create temporary directory"

    metadata="$tmp/release.json"

    curl \
        -fL \
        --retry 3 \
        --connect-timeout 15 \
        -H "Accept: application/vnd.github+json" \
        -H "User-Agent: NUNU-AI-Usage-Linux-installer" \
        "https://api.github.com/repos/steipete/CodexBar/releases/latest" \
        -o "$metadata"

    if [ "$?" -ne 0 ]; then
        rm -rf "$tmp"
        die "Could not retrieve CodexBar release metadata"
    fi

    asset_info=$(
        python3 - "$metadata" "$arch" <<'PY'
import json
import re
import sys

path = sys.argv[1]
arch = sys.argv[2]

with open(path, "r", encoding="utf-8") as handle:
    release = json.load(handle)

assets = {
    item.get("name"): item.get("browser_download_url")
    for item in release.get("assets", [])
    if item.get("name") and item.get("browser_download_url")
}

pattern = re.compile(
    r"^CodexBarCLI-v.+-linux-musl-"
    + re.escape(arch)
    + r"\.tar\.gz$"
)

names = [
    name
    for name in assets
    if pattern.match(name)
]

# Fall back to the glibc build if a musl archive
# is ever absent from a release.
if not names:
    pattern = re.compile(
        r"^CodexBarCLI-v.+-linux-"
        + re.escape(arch)
        + r"\.tar\.gz$"
    )

    names = [
        name
        for name in assets
        if pattern.match(name)
    ]

if len(names) != 1:
    raise SystemExit(
        "Could not identify one CodexBar Linux archive"
    )

archive_name = names[0]
checksum_name = archive_name + ".sha256"

if checksum_name not in assets:
    raise SystemExit(
        "Matching SHA-256 asset is missing"
    )

print(archive_name)
print(assets[archive_name])
print(checksum_name)
print(assets[checksum_name])
PY
    )

    if [ "$?" -ne 0 ]; then
        rm -rf "$tmp"
        die "Could not select CodexBar release assets"
    fi

    archive_name=$(printf '%s\n' "$asset_info" | sed -n '1p')
    archive_url=$(printf '%s\n' "$asset_info" | sed -n '2p')
    checksum_name=$(printf '%s\n' "$asset_info" | sed -n '3p')
    checksum_url=$(printf '%s\n' "$asset_info" | sed -n '4p')

    [ -n "$archive_name" ] ||
        die "Empty CodexBar archive name"

    archive="$tmp/$archive_name"
    checksum="$tmp/$checksum_name"

    say "Downloading:"
    say "  $archive_name"

    curl \
        -fL \
        --retry 3 \
        --connect-timeout 15 \
        "$archive_url" \
        -o "$archive" ||
    {
        rm -rf "$tmp"
        die "Could not download CodexBar archive"
    }

    curl \
        -fL \
        --retry 3 \
        --connect-timeout 15 \
        "$checksum_url" \
        -o "$checksum" ||
    {
        rm -rf "$tmp"
        die "Could not download CodexBar checksum"
    }

    expected=$(
        awk 'NR == 1 { print $1 }' "$checksum"
    )

    actual=$(
        sha256sum "$archive" |
        awk '{ print $1 }'
    )

    case "$expected" in
        [0-9a-fA-F][0-9a-fA-F]*)
            ;;
        *)
            rm -rf "$tmp"
            die "Invalid published CodexBar checksum"
            ;;
    esac

    if [ "$expected" != "$actual" ]; then
        rm -rf "$tmp"
        die "CodexBar SHA-256 verification failed"
    fi

    say "CodexBar SHA-256 verified."

    extract="$tmp/extract"

    mkdir -p "$extract" ||
        die "Could not create extraction directory"

    tar -xzf "$archive" -C "$extract" ||
    {
        rm -rf "$tmp"
        die "Could not extract CodexBar archive"
    }

    cli=$(
        find "$extract" \
            -type f \
            -name CodexBarCLI \
            -print \
            -quit
    )

    [ -n "$cli" ] ||
    {
        rm -rf "$tmp"
        die "CodexBarCLI not found inside archive"
    }

    bundle=$(
        find "$extract" \
            -type d \
            -name CodexBar_CodexBarCore.bundle \
            -print \
            -quit
    )

    install -d -m 755 "$CODEXBAR_ROOT"

    install -m 755 \
        "$cli" \
        "$CODEXBAR_BIN"

    if [ -n "$bundle" ]; then
        rm -rf \
            "$CODEXBAR_ROOT/CodexBar_CodexBarCore.bundle"

        cp -a \
            "$bundle" \
            "$CODEXBAR_ROOT/CodexBar_CodexBarCore.bundle"
    fi

    version_file=$(
        find "$extract" \
            -type f \
            -name VERSION \
            -print \
            -quit
    )

    if [ -n "$version_file" ]; then
        install -m 644 \
            "$version_file" \
            "$CODEXBAR_ROOT/VERSION"
    fi

    rm -rf "$tmp"

    [ -x "$CODEXBAR_BIN" ] ||
        die "CodexBar installation did not produce an executable CLI"

    say "Installed CodexBarCLI:"
    say "  $CODEXBAR_BIN"
}


enable_desklet_if_requested() {
    if [ "$INSTALL_DESKLET" -eq 0 ]; then
        say "Cinnamon Desklet enable skipped on $DESKTOP_KIND."
        return
    fi

    if [ "$ENABLE_DESKLET" -eq 0 ]; then
        say "Desklet enable skipped."
        return
    fi

    current=$(
        gsettings get \
            org.cinnamon \
            enabled-desklets \
            2>/dev/null
    )

    if [ "$?" -ne 0 ]; then
        say "Could not read Cinnamon enabled-desklets."
        say "Desklet files are installed but not enabled."
        return
    fi

    ENABLED_DESKLETS="$current" \
    DESKLET_UUID="$DESKLET_UUID" \
    python3 - <<'PY'
import ast
import os
import re
import subprocess

uuid = os.environ["DESKLET_UUID"]

try:
    items = ast.literal_eval(
        os.environ["ENABLED_DESKLETS"]
    )
except Exception:
    raise SystemExit(
        "Could not parse Cinnamon enabled-desklets"
    )

if any(
    item.startswith(uuid + ":")
    for item in items
):
    print("Desklet is already enabled.")
    raise SystemExit(0)

instance_ids = []

for item in items:
    parts = item.split(":")

    if len(parts) >= 2:
        try:
            instance_ids.append(
                int(parts[1])
            )
        except ValueError:
            pass

instance_id = (
    max(instance_ids) + 1
    if instance_ids
    else 1
)

x = 32
y = 32

try:
    output = subprocess.check_output(
        ["xrandr", "--listmonitors"],
        text=True,
        stderr=subprocess.DEVNULL,
    )

    for line in output.splitlines()[1:]:
        if "*" not in line:
            continue

        match = re.search(
            r"(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)",
            line,
        )

        if match:
            x = int(match.group(3)) + 32
            y = int(match.group(4)) + 32

        break

except Exception:
    pass

entry = "{}:{}:{}:{}".format(
    uuid,
    instance_id,
    x,
    y,
)

items.append(entry)

subprocess.run(
    [
        "gsettings",
        "set",
        "org.cinnamon",
        "enabled-desklets",
        repr(items),
    ],
    check=True,
)

print("Enabled:", entry)
PY

    if [ "$?" -ne 0 ]; then
        say "Desklet files installed, but automatic enable failed."
        say "Enable NUNU from Cinnamon Desklets settings."
    fi
}


smoke_test() {
    say "Running local smoke test..."

    output=$(
        "$BIN_ROOT/nunu-ai-usage" 2>/dev/null
    )

    if [ "$?" -ne 0 ]; then
        die "Installed backend command failed"
    fi

    NUNU_OUTPUT="$output" python3 - <<'PY'
import json
import os

data = json.loads(
    os.environ["NUNU_OUTPUT"]
)

if not isinstance(data, dict):
    raise SystemExit(
        "Widget output is not a JSON object"
    )

if "accounts" not in data:
    raise SystemExit(
        "Widget output does not contain accounts"
    )
PY

    if [ "$?" -ne 0 ]; then
        die "Installed backend returned invalid widget JSON"
    fi
}


main() {
    say "NUNU AI Usage Linux installer"
    say "============================="

    detect_desktop
    check_runtime_dependencies
    install_app_files
    install_config
    install_launchers
    install_application_launcher
    install_autostart
    install_desklet
    install_codexbar_if_needed
    enable_desklet_if_requested
    smoke_test

    say
    say "Install complete."
    say
    say "Commands:"
    say "  nunu-ai-usage"
    say "  nunu-ai-usage-settings"
    say "  nunu-ai-usage-widget"
    say
    say "Desktop integration:"
    if [ "$INSTALL_DESKLET" -eq 1 ]; then
        say "  Cinnamon Desklet"
    else
        say "  Universal GTK floating widget"
        say "  Autostart: $AUTOSTART_FILE"
    fi
    say
    say "Application:"
    say "  $APP_ROOT"
    say
    say "Application menu:"
    say "  $APPLICATION_FILE"
    say
    say "Config:"
    say "  $CONFIG_FILE"
    say
    say "Managed provider profiles are kept separately at:"
    say "  $PROFILE_ROOT"
    say
    say "NUNU does not copy or delete your provider credentials."
}


main "$@"
