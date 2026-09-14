# NUNU AI Usage Linux

A lightweight Cinnamon desktop widget for viewing AI usage quotas at a glance.

Version: **0.1.0**

## Features

- OpenAI Codex usage
- Anthropic Claude usage
- Multiple accounts
- Existing and isolated managed accounts
- LEFT / USED quota display
- Manual and automatic refresh
- Account show/hide, rename, reconnect and remove
- Multi-monitor support
- Four-corner positioning
- Monitor disconnect/reconnect recovery
- Safe per-user installation

## Tested platform

- Linux Mint 22.2
- Cinnamon 6.4
- X11

Version 0.1.0 uses XRandR for monitor placement.

## Requirements

- Python 3
- GTK 3 Python bindings
- Cinnamon
- gsettings
- xrandr
- Codex CLI and/or Claude CLI

NUNU also uses CodexBarCLI for provider usage retrieval.

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

Print sanitized widget data:

    nunu-ai-usage

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

## Multi-monitor

Settings support:

- Primary monitor
- Individual display connectors
- Top left
- Top right
- Bottom left
- Bottom right

If a selected external monitor disconnects, NUNU temporarily falls back to
the primary monitor and returns when the selected monitor reconnects.

## Uninstall

Safe default uninstall:

    ./uninstall.sh

By default NUNU preserves configuration, managed provider profiles,
provider-native profiles, and CodexBarCLI.

Optional destructive cleanup:

    ./uninstall.sh --delete-config
    ./uninstall.sh --delete-profiles

## Documentation

See the `docs/` directory for installation, provider and account details.

## License

MIT License. See `LICENSE`.

Third-party software is covered by its own licenses. See
`THIRD_PARTY_NOTICES.md`.
