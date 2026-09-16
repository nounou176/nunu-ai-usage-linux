# NUNU AI Usage Linux

*(Bản tiếng Việt: [README.vi.md](README.vi.md))*

## What is it for?

See your Claude and Codex usage right on your desktop — no terminal needed.

![Desktop overview](screenshots/desktop_overview.png)

## Features

- View Claude and Codex usage directly on the desktop
- Support for multiple accounts
- Freely customize the widget's position and appearance
- Automatic refresh (manual refresh also available)
- Multi-monitor support
- Works with Cinnamon (native Desklet) and Xfce/MATE (Universal GTK widget)

### Cinnamon

Setting | Display
:---: | :---:
![Cinnamon setting](screenshots/cinnamon_setting.png) | ![Cinnamon display](screenshots/cinnamon_display.png)

### Xfce

Setting | Display
:---: | :---:
![Xfce setting](screenshots/xfce_setting.png) | ![Xfce display](screenshots/xfce_display.png)

## Requirements

- Python 3
- GTK 3 Python bindings
- xrandr
- Codex CLI and/or Claude CLI (depending on the provider you use)
- Cinnamon additionally requires `gsettings` for automatic Desklet integration

## Install

```bash
git clone https://github.com/nounou176/nunu-ai-usage-linux.git
cd nunu-ai-usage-linux
chmod +x install.sh
./install.sh
```

No sudo required — the installer works per-user.

## Commands

```bash
nunu-ai-usage-settings   # Open the Settings window
nunu-ai-usage            # Print usage data
nunu-ai-usage-widget     # Run the widget manually (Xfce/MATE)
```

## Uninstall

```bash
./uninstall.sh
```

By default, configuration, saved accounts and CodexBarCLI are preserved.
See `./uninstall.sh --help` for all options.

## Documentation

See the `docs/` directory for installation, provider and account details.

See [CHANGELOG.md](CHANGELOG.md) for the full release history.

## License

MIT — see [LICENSE](LICENSE).
