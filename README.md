# NUNU AI Usage Linux

A lightweight desktop widget for viewing Codex and Claude usage quotas at a glance.

Version: **0.2.0**

## Features

- OpenAI Codex usage
- Anthropic Claude usage
- Multiple accounts
- Existing and isolated managed accounts
- LEFT / USED quota display
- Manual and automatic refresh
- Account show/hide, rename, reconnect and remove
- Universal GTK floating widget
- Cinnamon Desklet compatibility
- Application Menu launcher
- Optional start automatically after login
- Keep-above preference
- Drag and persistent widget placement
- Multi-monitor-aware placement
- Four-corner positioning
- Monitor disconnect/reconnect fallback
- Safe per-user installation and uninstall

## Desktop integration

NUNU detects the current desktop during installation.

### Xfce and other compatible X11 desktops

NUNU installs the Universal GTK floating widget:

    nunu-ai-usage-widget

It also installs:

    ~/.local/share/applications/nunu-ai-usage.desktop
    ~/.config/autostart/nunu-ai-usage-widget.desktop

Autostart can be disabled from NUNU Settings.

### Cinnamon

NUNU retains the native Cinnamon Desklet integration from version 0.1.

On Cinnamon, the installer installs the Desklet rather than starting the
Universal GTK widget automatically.

### MATE

The installer contains a Universal GTK integration path for MATE.

MATE has not yet received the same real-desktop regression validation as Xfce,
so it should currently be considered compatible but not fully validated.

## Tested platform

Version 0.2.0 release validation:

- Linux Mint
- Xfce
- X11

The complete v0.2 install, singleton, autostart preference, configuration
preservation, uninstall and backend smoke-test flow has been regression-tested
on Xfce/X11.

Cinnamon Desklet compatibility is retained from v0.1.0. A dedicated v0.2
Cinnamon regression pass is still pending.

Version 0.2.0 uses XRandR for monitor discovery and placement, so Wayland is
not currently an officially supported target.

## Requirements

- Python 3
- GTK 3 Python bindings
- xrandr
- Codex CLI and/or Claude CLI

Cinnamon additionally requires `gsettings` for automatic Desklet integration.

NUNU uses CodexBarCLI for provider usage retrieval.

CodexBarCLI is not bundled in this repository. The installer can download an
official upstream Linux release and verify its published SHA-256 checksum.

## Install

Clone the repository:

    git clone https://github.com/nounou176/nunu-ai-usage-linux.git
    cd nunu-ai-usage-linux

Install:

    chmod +x install.sh
    ./install.sh

No sudo is required.

## Commands

Open Settings:

    nunu-ai-usage-settings

Open the Universal GTK widget:

    nunu-ai-usage-widget

Print sanitized widget data:

    nunu-ai-usage

## Settings

The Settings application can manage:

- LEFT / USED display mode
- Refresh interval
- Widget position
- Keep widget above other windows
- Start automatically after login
- Codex and Claude accounts

## Accounts

NUNU can use provider accounts already authenticated on the computer.

Additional accounts can use isolated local profiles stored under:

    ~/.local/share/nunu-ai-usage-linux/profiles/

Removing an account from NUNU does not automatically delete its provider
profile or log the provider account out.

## Privacy

NUNU configuration stores account metadata rather than passwords, tokens,
cookies, or provider authentication files.

Important permissions:

    ~/.config/nunu-ai-usage-linux/                 0700
    ~/.config/nunu-ai-usage-linux/config.json      0600
    ~/.local/share/nunu-ai-usage-linux/            0700
    ~/.local/share/nunu-ai-usage-linux/profiles/   0700

NUNU-managed profiles and provider-native profiles are not removed by the
default uninstall.

## Widget placement

The Universal GTK widget supports persistent placement and stores its position
as monitor, anchor and margins.

If a configured monitor is unavailable, NUNU falls back to the primary
monitor.

Multi-monitor code is retained, but the v0.2.0 release regression was performed
with a single active display.

## Uninstall

Safe default uninstall:

    ./uninstall.sh

The default uninstall removes NUNU application files, launchers, desktop
integration, runtime cache and the Cinnamon Desklet when present.

It preserves:

    ~/.config/nunu-ai-usage-linux/
    ~/.local/share/nunu-ai-usage-linux/profiles/
    ~/.local/opt/codexbar/

Provider-native profiles such as `~/.codex` and `~/.claude` are also left
untouched.

Optional destructive cleanup:

    ./uninstall.sh --delete-config
    ./uninstall.sh --delete-profiles

## Documentation

See the `docs/` directory for installation, provider and account details.

## License

MIT License. See `LICENSE`.

Third-party software is covered by its own licenses. See
`THIRD_PARTY_NOTICES.md`.
