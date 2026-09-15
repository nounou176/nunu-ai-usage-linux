# Changelog

## [0.2.0] - 2026-09-15

Universal desktop integration release.

### Added

- Universal GTK floating widget
- Xfce desktop integration
- Application Menu launcher
- XDG autostart integration
- Widget singleton protection
- Drag-and-save widget placement
- Keep-above widget preference
- Start-after-login preference
- Runtime synchronization of widget settings
- Universal-aware installer desktop detection

### Changed

- Settings UI now describes the desktop display as a Widget rather than a
  Cinnamon-only Desklet
- Reset-time presentation is normalized for Codex and Claude
- Widget launcher detaches stdin so background execution does not become a
  stopped terminal job
- Installer preserves the user's autostart preference
- Monitor selection is kept internally while the v0.2 Settings UI is simplified
  for the common single-display workflow
- Uninstaller now removes Universal GTK launchers, Application Menu integration,
  autostart integration and runtime cache

### Safety

- Default uninstall continues to preserve configuration
- Default uninstall continues to preserve managed provider profiles
- Provider-native Codex and Claude profiles are not removed
- CodexBarCLI is not removed
- Widget process shutdown validates the lock PID before sending a signal

### Validation

- Full v0.2 regression completed on Linux Mint with Xfce/X11
- Install and uninstall flows validated in isolated HOME directories
- Singleton behavior validated
- Autostart-disabled preference validated across reinstall
- Existing backend presentation and provider smoke tests pass
- Cinnamon Desklet compatibility is retained from v0.1.0, but a dedicated
  v0.2 Cinnamon regression pass is still pending
- MATE integration exists but has not yet been validated on a real MATE session

## [0.1.0] - 2026-09-14

Initial public release.

### Added

- Cinnamon AI usage Desklet
- OpenAI Codex provider
- Anthropic Claude provider
- Multiple accounts
- Existing and isolated managed accounts
- LEFT / USED display
- Manual and automatic refresh
- Account visibility, rename, reconnect and safe remove
- GTK Settings UI
- Multi-monitor selection
- Four-corner positioning
- Monitor disconnect/reconnect fallback
- Dead-zone recovery
- Persistent Desklet placement
- Per-user installer
- Safe uninstaller
- Sanitized widget-data output
- Restricted config and profile permissions
- Optional verified CodexBarCLI installation

### Platform

Tested on Linux Mint 22.2, Cinnamon 6.4, X11.
