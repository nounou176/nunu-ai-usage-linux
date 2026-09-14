#!/bin/sh

# NUNU AI Usage Linux
# Safe per-user uninstaller.
#
# Default behavior:
# - disables only the public NUNU Desklet
# - removes NUNU application files
# - removes NUNU launchers
# - removes NUNU Desklet files
# - PRESERVES config
# - PRESERVES managed login profiles
# - PRESERVES CodexBarCLI
#
# Optional destructive cleanup must be requested explicitly.

set -u

APP_ID="nunu-ai-usage-linux"
DESKLET_UUID="nunu-ai-usage-linux@nunu"

DATA_ROOT="$HOME/.local/share/$APP_ID"
APP_ROOT="$DATA_ROOT/app"
PROFILE_ROOT="$DATA_ROOT/profiles"

CONFIG_ROOT="$HOME/.config/$APP_ID"

BIN_ROOT="$HOME/.local/bin"

BACKEND_LAUNCHER="$BIN_ROOT/nunu-ai-usage"
SETTINGS_LAUNCHER="$BIN_ROOT/nunu-ai-usage-settings"

DESKLET_ROOT="$HOME/.local/share/cinnamon/desklets"
DESKLET_DEST="$DESKLET_ROOT/$DESKLET_UUID"

DELETE_CONFIG=0
DELETE_PROFILES=0
DISABLE_DESKLET=1


say() {
    printf '%s\n' "$*"
}


die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}


usage() {
    cat <<'EOF'
Usage: ./uninstall.sh [options]

Default uninstall preserves:
  ~/.config/nunu-ai-usage-linux/
  ~/.local/share/nunu-ai-usage-linux/profiles/
  ~/.local/opt/codexbar/

Options:
  --delete-config
      Also delete NUNU settings/config.

  --delete-profiles
      Also delete NUNU-managed provider profiles.
      WARNING: these profiles may contain active login sessions.

  --no-disable
      Do not modify Cinnamon enabled-desklets.
      Useful for packaging/tests.

  -h, --help
      Show this help.
EOF
}


while [ "$#" -gt 0 ]; do
    case "$1" in
        --delete-config)
            DELETE_CONFIG=1
            ;;

        --delete-profiles)
            DELETE_PROFILES=1
            ;;

        --no-disable)
            DISABLE_DESKLET=0
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


safe_remove_file() {
    path="$1"

    case "$path" in
        "$HOME"/.local/bin/*)
            ;;
        *)
            die "Refusing unexpected file path: $path"
            ;;
    esac

    if [ -e "$path" ] || [ -L "$path" ]; then
        rm -f -- "$path" ||
            die "Could not remove: $path"

        say "Removed:"
        say "  $path"
    fi
}


safe_remove_tree() {
    path="$1"

    case "$path" in
        "$HOME"/.local/share/nunu-ai-usage-linux/app)
            ;;

        "$HOME"/.local/share/cinnamon/desklets/nunu-ai-usage-linux@nunu)
            ;;

        "$HOME"/.config/nunu-ai-usage-linux)
            ;;

        "$HOME"/.local/share/nunu-ai-usage-linux/profiles)
            ;;

        *)
            die "Refusing unexpected directory path: $path"
            ;;
    esac

    if [ -d "$path" ] || [ -L "$path" ]; then
        rm -rf -- "$path" ||
            die "Could not remove: $path"

        say "Removed:"
        say "  $path"
    fi
}


disable_public_desklet() {
    if [ "$DISABLE_DESKLET" -eq 0 ]; then
        say "Cinnamon Desklet disable skipped."
        return
    fi

    if ! command -v gsettings >/dev/null 2>&1; then
        say "gsettings not available; Desklet disable skipped."
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
        return
    fi

    ENABLED_DESKLETS="$current" \
    DESKLET_UUID="$DESKLET_UUID" \
    python3 - <<'PY'
import ast
import os
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

kept = [
    item
    for item in items
    if not item.startswith(uuid + ":")
]

removed = len(items) - len(kept)

if removed == 0:
    print("Public NUNU Desklet was not enabled.")
    raise SystemExit(0)

subprocess.run(
    [
        "gsettings",
        "set",
        "org.cinnamon",
        "enabled-desklets",
        repr(kept),
    ],
    check=True,
)

print(
    "Disabled {} public NUNU Desklet instance(s).".format(
        removed
    )
)
PY

    if [ "$?" -ne 0 ]; then
        say "Warning: automatic Desklet disable failed."
    fi
}


cleanup_empty_data_root() {
    # DATA_ROOT may still contain managed profiles.
    # Never remove it unless it is genuinely empty.
    if [ ! -d "$DATA_ROOT" ]; then
        return
    fi

    if [ -z "$(find "$DATA_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
        rmdir "$DATA_ROOT" 2>/dev/null || true
    fi
}


main() {
    say "NUNU AI Usage Linux uninstaller"
    say "==============================="

    disable_public_desklet

    safe_remove_file \
        "$BACKEND_LAUNCHER"

    safe_remove_file \
        "$SETTINGS_LAUNCHER"

    safe_remove_tree \
        "$DESKLET_DEST"

    safe_remove_tree \
        "$APP_ROOT"

    if [ "$DELETE_CONFIG" -eq 1 ]; then
        safe_remove_tree \
            "$CONFIG_ROOT"
    else
        say
        say "Preserved config:"
        say "  $CONFIG_ROOT"
    fi

    if [ "$DELETE_PROFILES" -eq 1 ]; then
        say
        say "Deleting managed provider profiles by explicit request."

        safe_remove_tree \
            "$PROFILE_ROOT"
    else
        say
        say "Preserved managed provider profiles:"
        say "  $PROFILE_ROOT"
    fi

    cleanup_empty_data_root

    say
    say "CodexBarCLI was not removed."
    say "Provider-native profiles such as ~/.codex and ~/.claude were not touched."

    say
    say "Uninstall complete."
}


main "$@"
