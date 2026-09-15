# Installation

## Requirements

NUNU AI Usage Linux 0.2 targets X11 desktops.

Required:

- Python 3
- GTK 3 Python bindings
- xrandr
- Codex CLI and/or Claude CLI when those providers are used

Cinnamon additionally requires `gsettings` for automatic Desklet integration.

The v0.2 release regression has been completed on Linux Mint with Xfce/X11.

Cinnamon keeps the native Desklet integration from v0.1. MATE uses the
Universal GTK widget path but has not yet received the same real-desktop
regression validation.

## Install

From the repository root:

    chmod +x install.sh
    ./install.sh

The installer works per-user and does not require sudo.

The installer detects Cinnamon, Xfce and MATE. Other compatible X11 desktops
fall back to the Universal GTK widget integration.

## Installed locations

Application:

    ~/.local/share/nunu-ai-usage-linux/app/

Commands:

    ~/.local/bin/nunu-ai-usage
    ~/.local/bin/nunu-ai-usage-settings
    ~/.local/bin/nunu-ai-usage-widget

Configuration:

    ~/.config/nunu-ai-usage-linux/config.json

Managed provider profiles:

    ~/.local/share/nunu-ai-usage-linux/profiles/

Application Menu launcher:

    ~/.local/share/applications/nunu-ai-usage.desktop

Universal-widget autostart, when enabled:

    ~/.config/autostart/nunu-ai-usage-widget.desktop

Cinnamon Desklet, when Cinnamon integration is selected:

    ~/.local/share/cinnamon/desklets/nunu-ai-usage-linux@nunu/

## Desktop behavior

On Xfce, MATE and compatible X11 desktops, NUNU uses the Universal GTK
floating widget.

On Cinnamon, NUNU installs the native Cinnamon Desklet and does not create a
duplicate floating-widget autostart entry.

The Universal widget can be started manually with:

    nunu-ai-usage-widget

Settings can be opened with:

    nunu-ai-usage-settings

## Uninstall

Safe default:

    ./uninstall.sh

The default uninstall removes installed NUNU application files, launchers,
desktop integration and runtime cache.

It preserves configuration, managed provider profiles, CodexBarCLI and
provider-native authentication profiles.

Optional destructive cleanup:

    ./uninstall.sh --delete-config
    ./uninstall.sh --delete-profiles

See:

    ./uninstall.sh --help

for all available options.
