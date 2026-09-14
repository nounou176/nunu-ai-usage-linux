# Installation

## Requirements

NUNU AI Usage Linux currently targets Cinnamon on X11.

Required tools include Python 3, GTK 3 Python bindings, gsettings and xrandr.

## Install

From the repository root:

    chmod +x install.sh
    ./install.sh

The installer works per-user and does not require sudo.

## Installed locations

Application:

    ~/.local/share/nunu-ai-usage-linux/app/

Desklet:

    ~/.local/share/cinnamon/desklets/nunu-ai-usage-linux@nunu/

Commands:

    ~/.local/bin/nunu-ai-usage
    ~/.local/bin/nunu-ai-usage-settings

Configuration:

    ~/.config/nunu-ai-usage-linux/config.json

## Uninstall

Safe default:

    ./uninstall.sh

See `./uninstall.sh --help` for optional cleanup flags.
