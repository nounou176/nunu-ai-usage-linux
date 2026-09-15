#!/usr/bin/env python3

import fcntl
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from nunu_ai_usage.widget_data import build_widget_data

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk


APP_TITLE = "NUNU AI Usage"

CACHE_ROOT = (
    Path.home()
    / ".cache"
    / "nunu-ai-usage-linux"
)

LOCK_PATH = (
    CACHE_ROOT
    / "widget.lock"
)

_SINGLETON_LOCK = None

CONFIG_PATH = (
    Path.home()
    / ".config"
    / "nunu-ai-usage-linux"
    / "config.json"
)


def acquire_singleton_lock():
    global _SINGLETON_LOCK

    CACHE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o700,
    )

    try:
        CACHE_ROOT.chmod(0o700)
    except OSError:
        pass

    handle = LOCK_PATH.open(
        "a+",
        encoding="utf-8",
    )

    try:
        LOCK_PATH.chmod(0o600)
    except OSError:
        pass

    try:
        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_EX
            | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        handle.seek(0)
        owner = handle.read().strip()

        if owner:
            print(
                "NUNU AI Usage widget is already "
                f"running (PID {owner})."
            )
        else:
            print(
                "NUNU AI Usage widget is already "
                "running."
            )

        handle.close()
        return False

    handle.seek(0)
    handle.truncate()
    handle.write(str(__import__("os").getpid()))
    handle.flush()

    _SINGLETON_LOCK = handle

    return True


def load_config():
    if not CONFIG_PATH.exists():
        return {
            "settings": {
                "display_mode": "left",
                "refresh_seconds": 60,
                "widget": {
                    "monitor": "primary",
                    "anchor": "top-right",
                    "margin_x": 32,
                    "margin_y": 32,
                    "keep_visible": True,
                },
            }
        }

    try:
        return json.loads(
            CONFIG_PATH.read_text(encoding="utf-8")
        )
    except Exception:
        return {
            "settings": {
                "display_mode": "left",
                "refresh_seconds": 60,
                "widget": {
                    "monitor": "primary",
                    "anchor": "top-right",
                    "margin_x": 32,
                    "margin_y": 32,
                    "keep_visible": True,
                },
            }
        }


def widget_settings():
    config = load_config()

    settings = config.get("settings", {})
    widget = settings.get("widget", {})

    return {
        "display_mode": settings.get(
            "display_mode",
            "left",
        ),
        "refresh_seconds": int(
            settings.get(
                "refresh_seconds",
                60,
            )
        ),
        "monitor": widget.get(
            "monitor",
            "primary",
        ),
        "anchor": widget.get(
            "anchor",
            "top-right",
        ),
        "margin_x": int(
            widget.get(
                "margin_x",
                32,
            )
        ),
        "margin_y": int(
            widget.get(
                "margin_y",
                32,
            )
        ),
        "keep_visible": bool(
            widget.get(
                "keep_visible",
                True,
            )
        ),
    }


def xrandr_monitors():
    try:
        output = subprocess.check_output(
            ["xrandr", "--listmonitors"],
            text=True,
        )
    except Exception:
        return []

    items = []

    for line in output.splitlines():
        line = line.strip()

        match = re.match(
            r"^\d+:\s+\+?\*?([^\s]+)\s+(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)",
            line,
        )

        if not match:
            continue

        connector = match.group(1)
        width = int(match.group(2))
        height = int(match.group(3))
        x = int(match.group(4))
        y = int(match.group(5))

        items.append(
            {
                "connector": connector,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            }
        )

    return items


def format_interval(seconds):
    seconds = int(seconds)

    if seconds % 3600 == 0:
        return "{}h".format(seconds // 3600)

    if seconds % 60 == 0:
        return "{}m".format(seconds // 60)

    return "{}s".format(seconds)


def format_generated_at(value):
    if not value:
        return "just now"

    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%-I:%M %p")
    except Exception:
        return str(value)


class FloatingWidget(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE)

        self._refresh_timer = 0
        self._placement_timer = 0
        self._refreshing = False

        self.set_name("nunu-window")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()
        self.set_type_hint(
            Gdk.WindowTypeHint.UTILITY
        )
        self.set_default_size(326, 100)

        self.connect(
            "destroy",
            self.on_destroy,
        )

        self.connect(
            "size-allocate",
            self.on_size_allocate,
        )

        screen = self.get_screen()

        if screen is not None:
            screen.connect(
                "monitors-changed",
                self.on_monitors_changed,
            )

        self._install_css()
        self._build_ui()

        GLib.idle_add(
            self._refresh_now
        )

    def _install_css(self):
        css = b"""
        #nunu-window {
            background: #0f1320;
            border-radius: 16px;
        }

        .nunu-root {
            background: #0f1320;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 16px;
        }

        .nunu-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }

        .nunu-account {
            font-size: 13px;
            font-weight: 700;
            color: #ffffff;
        }

        .nunu-dim {
            font-size: 11px;
            color: rgba(255,255,255,0.62);
        }

        .nunu-small {
            font-size: 11px;
            color: rgba(255,255,255,0.72);
        }

        .nunu-footer {
            font-size: 11px;
            color: rgba(255,255,255,0.50);
        }

        .nunu-button {
            padding: 4px 8px;
        }

        progressbar trough {
            min-height: 6px;
            border-radius: 99px;
            background: rgba(255,255,255,0.14);
        }

        progressbar progress {
            min-height: 6px;
            border-radius: 99px;
            background: #d9d9d9;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        outer.get_style_context().add_class(
            "nunu-root"
        )
        self.add(outer)

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        title = Gtk.Label(
            label=APP_TITLE,
            xalign=0,
        )
        title.get_style_context().add_class(
            "nunu-title"
        )

        header.pack_start(
            title,
            True,
            True,
            0,
        )

        refresh_button = Gtk.Button(
            label="↻"
        )
        refresh_button.get_style_context().add_class(
            "nunu-button"
        )
        refresh_button.connect(
            "clicked",
            self.on_refresh_clicked,
        )

        settings_button = Gtk.Button(
            label="⚙"
        )
        settings_button.get_style_context().add_class(
            "nunu-button"
        )
        settings_button.connect(
            "clicked",
            self.on_settings_clicked,
        )

        close_button = Gtk.Button(
            label="✕"
        )
        close_button.get_style_context().add_class(
            "nunu-button"
        )
        close_button.connect(
            "clicked",
            self.on_close_clicked,
        )

        header.pack_end(
            close_button,
            False,
            False,
            0,
        )

        header.pack_end(
            settings_button,
            False,
            False,
            0,
        )

        header.pack_end(
            refresh_button,
            False,
            False,
            0,
        )

        outer.pack_start(
            header,
            False,
            False,
            0,
        )

        self.status_label = Gtk.Label(
            label="Loading…",
            xalign=0,
        )
        self.status_label.get_style_context().add_class(
            "nunu-dim"
        )

        outer.pack_start(
            self.status_label,
            False,
            False,
            0,
        )

        self.content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )

        outer.pack_start(
            self.content_box,
            False,
            False,
            0,
        )

        self.footer_label = Gtk.Label(
            label="",
            xalign=0,
        )
        self.footer_label.get_style_context().add_class(
            "nunu-footer"
        )

        outer.pack_start(
            self.footer_label,
            False,
            False,
            0,
        )

    def clear_content(self):
        for child in self.content_box.get_children():
            self.content_box.remove(child)

    def divider(self):
        sep = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL
        )
        return sep

    def account_heading(self, text):
        label = Gtk.Label(
            label=text,
            xalign=0,
        )
        label.get_style_context().add_class(
            "nunu-account"
        )
        return label

    def small_label(self, text):
        label = Gtk.Label(
            label=text,
            xalign=0,
        )
        label.get_style_context().add_class(
            "nunu-small"
        )
        return label

    def dim_label(self, text):
        label = Gtk.Label(
            label=text,
            xalign=0,
        )
        label.get_style_context().add_class(
            "nunu-dim"
        )
        return label

    def usage_block(self, item):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )

        title_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        name = Gtk.Label(
            label=str(
                item.get("name", "Usage")
            ),
            xalign=0,
        )
        name.get_style_context().add_class(
            "nunu-account"
        )

        percent = int(
            item.get("display_percent", 0)
        )
        suffix = str(
            item.get("display_suffix", "USED")
        )

        value = Gtk.Label(
            label="{}% {}".format(
                percent,
                suffix,
            ),
            xalign=1,
        )
        value.get_style_context().add_class(
            "nunu-account"
        )

        title_row.pack_start(
            name,
            True,
            True,
            0,
        )
        title_row.pack_end(
            value,
            False,
            False,
            0,
        )

        box.pack_start(
            title_row,
            False,
            False,
            0,
        )

        progress = Gtk.ProgressBar()
        progress.set_fraction(
            max(
                0.0,
                min(1.0, percent / 100.0),
            )
        )

        box.pack_start(
            progress,
            False,
            False,
            0,
        )

        reset_text = str(
            item.get("reset_text", "")
        ).strip()

        if reset_text:
            box.pack_start(
                self.dim_label(
                    "Resets {}".format(
                        reset_text
                    )
                ),
                False,
                False,
                0,
            )

        return box

    def render_data(self, data):
        self.clear_content()

        accounts = data.get("accounts", [])

        if not accounts:
            self.status_label.set_text(
                "No visible accounts."
            )
        else:
            self.status_label.set_text(
                "Loaded {} account(s).".format(
                    len(accounts)
                )
            )

        first = True

        for account in accounts:
            if not first:
                self.content_box.pack_start(
                    self.divider(),
                    False,
                    False,
                    0,
                )

            first = False

            provider_name = str(
                account.get(
                    "provider_name",
                    account.get(
                        "provider",
                        "Provider",
                    ),
                )
            )

            label = str(
                account.get(
                    "label",
                    "Account",
                )
            )

            self.content_box.pack_start(
                self.account_heading(
                    "{} · {}".format(
                        provider_name,
                        label,
                    )
                ),
                False,
                False,
                0,
            )

            if not account.get("ok"):
                message = str(
                    account.get(
                        "message",
                        "Usage unavailable",
                    )
                )
                self.content_box.pack_start(
                    self.dim_label(message),
                    False,
                    False,
                    0,
                )
                continue

            windows = account.get("windows", [])

            if not windows:
                self.content_box.pack_start(
                    self.dim_label(
                        "No usage windows."
                    ),
                    False,
                    False,
                    0,
                )
                continue

            for item in windows:
                self.content_box.pack_start(
                    self.usage_block(item),
                    False,
                    False,
                    0,
                )

        refresh_seconds = int(
            data.get(
                "refresh_seconds",
                60,
            )
        )

        generated_at = format_generated_at(
            data.get("generated_at")
        )

        self.footer_label.set_text(
            "Updated {} · {}".format(
                generated_at,
                format_interval(
                    refresh_seconds
                ),
            )
        )

        self.show_all()
        self.schedule_placement(30)
        self.schedule_refresh(refresh_seconds)

    def render_error(self, message):
        self.clear_content()
        self.status_label.set_text(
            "Could not load widget data."
        )
        self.content_box.pack_start(
            self.dim_label(str(message)),
            False,
            False,
            0,
        )
        self.footer_label.set_text("")
        self.show_all()
        self.schedule_refresh(30)
        self.schedule_placement(30)

    def schedule_refresh(self, seconds):
        seconds = max(5, int(seconds))

        if self._refresh_timer:
            GLib.source_remove(
                self._refresh_timer
            )
            self._refresh_timer = 0

        self._refresh_timer = GLib.timeout_add_seconds(
            seconds,
            self._refresh_now,
        )

    def _refresh_now(self):
        if self._refreshing:
            return False

        self._refreshing = True
        self.status_label.set_text(
            "Refreshing…"
        )

        try:
            data = build_widget_data()
            self.render_data(data)
        except Exception as exc:
            self.render_error(exc)
        finally:
            self._refreshing = False

        return False

    def schedule_placement(self, delay_ms=50):
        if self._placement_timer:
            GLib.source_remove(
                self._placement_timer
            )
            self._placement_timer = 0

        self._placement_timer = GLib.timeout_add(
            delay_ms,
            self._apply_placement,
        )

    def _resolve_gdk_monitor(self, config):
        display = Gdk.Display.get_default()

        if display is None:
            return None

        name = str(
            config.get(
                "monitor",
                "primary",
            )
        )

        if name == "primary":
            return display.get_primary_monitor()

        target = None

        for item in xrandr_monitors():
            if item["connector"] == name:
                target = item
                break

        if target is None:
            return display.get_primary_monitor()

        for i in range(display.get_n_monitors()):
            monitor = display.get_monitor(i)

            if monitor is None:
                continue

            rect = monitor.get_geometry()

            if (
                rect.x == target["x"]
                and rect.y == target["y"]
                and rect.width == target["width"]
                and rect.height == target["height"]
            ):
                return monitor

        return display.get_primary_monitor()

    def _monitor_rect(self, monitor):
        if monitor is None:
            return None

        try:
            rect = monitor.get_workarea()
        except Exception:
            rect = monitor.get_geometry()

        return rect

    def _apply_placement(self):
        self._placement_timer = 0

        config = widget_settings()
        monitor = self._resolve_gdk_monitor(config)
        rect = self._monitor_rect(monitor)

        if rect is None:
            return False

        width = self.get_allocated_width()
        height = self.get_allocated_height()

        if width <= 1 or height <= 1:
            return False

        margin_x = int(
            config.get(
                "margin_x",
                32,
            )
        )

        margin_y = int(
            config.get(
                "margin_y",
                32,
            )
        )

        anchor = str(
            config.get(
                "anchor",
                "top-right",
            )
        )

        if anchor == "top-left":
            x = rect.x + margin_x
            y = rect.y + margin_y

        elif anchor == "bottom-left":
            x = rect.x + margin_x
            y = rect.y + rect.height - height - margin_y

        elif anchor == "bottom-right":
            x = rect.x + rect.width - width - margin_x
            y = rect.y + rect.height - height - margin_y

        else:
            x = rect.x + rect.width - width - margin_x
            y = rect.y + margin_y

        self.move(x, y)
        return False

    def on_refresh_clicked(self, button):
        self._refresh_now()

    def on_settings_clicked(self, button):
        settings_py = (
            PROJECT_ROOT
            / "gui"
            / "account_manager.py"
        )

        subprocess.Popen(
            [
                sys.executable,
                str(settings_py),
            ]
        )

    def on_close_clicked(self, button):
        self.destroy()

    def on_size_allocate(self, *args):
        self.schedule_placement(20)

    def on_monitors_changed(self, *args):
        self.schedule_placement(150)

    def on_destroy(self, *args):
        if self._refresh_timer:
            GLib.source_remove(
                self._refresh_timer
            )
            self._refresh_timer = 0

        if self._placement_timer:
            GLib.source_remove(
                self._placement_timer
            )
            self._placement_timer = 0

        Gtk.main_quit()


def main():
    if not acquire_singleton_lock():
        return 0

    win = FloatingWidget()
    win.show_all()
    Gtk.main()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
