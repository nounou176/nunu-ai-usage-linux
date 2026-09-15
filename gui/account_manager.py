#!/usr/bin/env python3

import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from nunu_ai_usage.account_discovery import detect_existing_account
from nunu_ai_usage.account_store import AccountStore
from nunu_ai_usage.account_service import use_existing_account
from nunu_ai_usage.login_session import (
    create_login_session,
    create_reconnect_session,
)
from nunu_ai_usage.login_runtime import start_login_runtime
from nunu_ai_usage.login_service import verify_login_session, save_login_session

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, GLib, Gtk
import subprocess


APP_TITLE = "NUNU AI Usage Linux"


class ProviderRow(Gtk.Box):
    def __init__(
        self,
        company,
        provider,
        provider_id,
        on_add,
    ):
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=16,
        )

        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(16)
        self.set_margin_end(16)

        text_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=3,
        )

        company_label = Gtk.Label(
            label=company,
            xalign=0,
        )

        company_label.get_style_context().add_class(
            "dim-label"
        )

        provider_label = Gtk.Label(
            xalign=0,
        )

        provider_label.set_markup(
            "<b>{}</b>".format(provider)
        )

        text_box.pack_start(
            company_label,
            False,
            False,
            0,
        )

        text_box.pack_start(
            provider_label,
            False,
            False,
            0,
        )

        button = Gtk.Button(
            label="Add"
        )

        button.set_size_request(
            90,
            36,
        )

        button.connect(
            "clicked",
            on_add,
            provider_id,
            provider,
        )

        self.pack_start(
            text_box,
            True,
            True,
            0,
        )

        self.pack_end(
            button,
            False,
            False,
            0,
        )


class ConfiguredAccountRow(Gtk.Box):
    def __init__(
        self,
        account,
        on_action,
    ):
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )

        self.account = account
        self.on_action = on_action

        self.set_size_request(
            -1,
            54,
        )

        self.set_margin_start(12)
        self.set_margin_end(6)

        info = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=1,
        )

        name = Gtk.Label(
            xalign=0,
        )

        name.set_markup(
            "<b>{}</b>".format(
                account["label"]
            )
        )

        provider_name = {
            "codex": "Codex",
            "claude": "Claude",
        }.get(
            account["provider"],
            account["provider"],
        )

        connection_type = (
            account
            .get("connection", {})
            .get("type", "unknown")
        )

        detail = Gtk.Label(
            label="{}  ·  {}".format(
                provider_name,
                connection_type,
            ),
            xalign=0,
        )

        detail.get_style_context().add_class(
            "dim-label"
        )

        info.pack_start(
            name,
            False,
            False,
            0,
        )

        info.pack_start(
            detail,
            False,
            False,
            0,
        )

        self.pack_start(
            info,
            True,
            True,
            0,
        )

        visible = account.get(
            "show_on_widget",
            True,
        )

        visibility = Gtk.Button()

        visibility.set_relief(
            Gtk.ReliefStyle.NONE
        )

        visibility.set_size_request(
            38,
            38,
        )

        visibility.set_image(
            Gtk.Image.new_from_icon_name(
                (
                    "view-reveal-symbolic"
                    if visible
                    else "view-conceal-symbolic"
                ),
                Gtk.IconSize.BUTTON,
            )
        )

        visibility.set_tooltip_text(
            (
                "Shown on desktop"
                if visible
                else "Hidden from desktop"
            )
        )

        visibility.connect(
            "clicked",
            self._visibility_clicked,
        )

        menu = Gtk.Button()

        menu.set_relief(
            Gtk.ReliefStyle.NONE
        )

        menu.set_size_request(
            38,
            38,
        )

        menu.set_image(
            Gtk.Image.new_from_icon_name(
                "open-menu-symbolic",
                Gtk.IconSize.BUTTON,
            )
        )

        menu.set_tooltip_text(
            "Account actions"
        )

        menu.connect(
            "clicked",
            self._show_menu,
        )

        self.pack_end(
            menu,
            False,
            False,
            0,
        )

        self.pack_end(
            visibility,
            False,
            False,
            0,
        )


    def _visibility_clicked(
        self,
        button,
    ):
        self.on_action(
            "visibility",
            self.account,
        )


    def _show_menu(
        self,
        button,
    ):
        menu = Gtk.Menu()

        for label, action in (
            ("Rename", "rename"),
            ("Refresh", "refresh"),
            ("Reconnect", "reconnect"),
            ("Remove from NUNU", "remove"),
        ):
            item = Gtk.MenuItem(
                label=label
            )

            item.connect(
                "activate",
                self._activate,
                action,
            )

            menu.append(item)

        menu.show_all()

        menu.popup_at_widget(
            button,
            Gdk.Gravity.SOUTH_EAST,
            Gdk.Gravity.NORTH_EAST,
            None,
        )


    def _activate(
        self,
        item,
        action,
    ):
        self.on_action(
            action,
            self.account,
        )


class AccountManager(Gtk.Window):
    def __init__(self):
        super().__init__(
            title=APP_TITLE
        )

        self.store = AccountStore()

        self.set_default_size(
            760,
            -1,
        )

        self.set_size_request(
            720,
            -1,
        )

        self.set_border_width(0)

        self.connect(
            "destroy",
            Gtk.main_quit,
        )

        screen = self.get_screen()

        if screen is not None:
            screen.connect(
                "monitors-changed",
                self._on_monitors_changed,
            )

        config = self.store.load()
        settings = config.get(
            "settings",
            {},
        )

        display_mode = settings.get(
            "display_mode",
            "left",
        )

        refresh_seconds = int(
            settings.get(
                "refresh_seconds",
                60,
            )
        )

        widget_settings = settings.get(
            "widget",
            {},
        )

        widget_monitor = widget_settings.get(
            "monitor",
            "primary",
        )

        widget_anchor = widget_settings.get(
            "anchor",
            "top-right",
        )

        widget_keep_visible = bool(
            widget_settings.get(
                "keep_visible",
                True,
            )
        )

        widget_autostart = bool(
            widget_settings.get(
                "autostart",
                True,
            )
        )

        self._draft_display_mode = display_mode
        self._draft_refresh_seconds = refresh_seconds
        self._draft_widget_monitor = widget_monitor
        self._draft_widget_anchor = widget_anchor
        self._draft_widget_keep_visible = (
            widget_keep_visible
        )
        self._draft_widget_autostart = (
            widget_autostart
        )
        self._settings_dirty = False
        self._updating_monitor_combo = False

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        self.add(root)

        # ==================================================
        # HEADER
        # ==================================================

        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )

        header.set_margin_top(11)
        header.set_margin_bottom(11)
        header.set_margin_start(16)
        header.set_margin_end(16)

        bunny = Gtk.Label()

        bunny.set_markup(
            "<span size=\"x-large\">🐰</span>"
        )

        header.pack_start(
            bunny,
            False,
            False,
            0,
        )

        header_text = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        title = Gtk.Label(
            xalign=0,
        )

        title.set_markup(
            "<span size=\"large\"><b>"
            "NUNU AI Usage"
            "</b></span>"
        )

        subtitle = Gtk.Label(
            label=(
                "Manage accounts and your AI usage widget."
            ),
            xalign=0,
        )

        subtitle.get_style_context().add_class(
            "dim-label"
        )

        header_text.pack_start(
            title,
            False,
            False,
            0,
        )

        header_text.pack_start(
            subtitle,
            False,
            False,
            0,
        )

        header.pack_start(
            header_text,
            True,
            True,
            0,
        )

        root.pack_start(
            header,
            False,
            False,
            0,
        )

        root.pack_start(
            Gtk.Separator(
                orientation=Gtk.Orientation.HORIZONTAL
            ),
            False,
            False,
            0,
        )

        # ==================================================
        # CONTENT
        # ==================================================

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )

        content.set_margin_top(12)
        content.set_margin_bottom(10)
        content.set_margin_start(16)
        content.set_margin_end(16)

        root.pack_start(
            content,
            False,
            False,
            0,
        )

        # ==================================================
        # ACCOUNTS
        # ==================================================

        accounts_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )

        section = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )

        heading = Gtk.Label(
            xalign=0,
        )

        heading.set_markup(
            "<b>Accounts</b>"
        )

        hint = Gtk.Label(
            label=(
                "Choose which accounts appear "
                "on the desktop widget."
            ),
            xalign=0,
        )

        hint.get_style_context().add_class(
            "dim-label"
        )

        section.pack_start(
            heading,
            False,
            False,
            0,
        )

        section.pack_start(
            hint,
            False,
            False,
            0,
        )

        accounts_header.pack_start(
            section,
            True,
            True,
            0,
        )

        add_button = Gtk.MenuButton(
            label="+  Add account"
        )

        add_menu = Gtk.Menu()

        add_codex = Gtk.MenuItem(
            label="Add Codex"
        )

        add_codex.connect(
            "activate",
            self.on_add_account,
            "codex",
            "Codex",
        )

        add_claude = Gtk.MenuItem(
            label="Add Claude"
        )

        add_claude.connect(
            "activate",
            self.on_add_account,
            "claude",
            "Claude",
        )

        add_menu.append(add_codex)
        add_menu.append(add_claude)
        add_menu.show_all()

        add_button.set_popup(
            add_menu
        )

        accounts_header.pack_end(
            add_button,
            False,
            False,
            0,
        )

        content.pack_start(
            accounts_header,
            False,
            False,
            0,
        )

        account_frame = Gtk.Frame()

        self.account_list = Gtk.ListBox()

        self.account_list.set_selection_mode(
            Gtk.SelectionMode.NONE
        )

        account_frame.add(
            self.account_list
        )

        content.pack_start(
            account_frame,
            False,
            False,
            2,
        )

        self.refresh_account_list()

        # ==================================================
        # DISPLAY
        # ==================================================

        divider = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        divider.set_margin_top(5)
        divider.set_margin_bottom(4)

        content.pack_start(
            divider,
            False,
            False,
            0,
        )

        display_title = Gtk.Label(
            xalign=0,
        )

        display_title.set_markup(
            "<b>Display</b>"
        )

        content.pack_start(
            display_title,
            False,
            False,
            0,
        )

        display_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )

        display_row.set_margin_top(2)

        usage_label = Gtk.Label(
            label="Usage",
        )

        display_row.pack_start(
            usage_label,
            False,
            False,
            0,
        )

        self.left_radio = (
            Gtk.RadioButton.new_with_label(
                None,
                "LEFT",
            )
        )

        self.used_radio = (
            Gtk.RadioButton.new_with_label_from_widget(
                self.left_radio,
                "USED",
            )
        )

        if display_mode == "used":
            self.used_radio.set_active(True)
        else:
            self.left_radio.set_active(True)

        self.left_radio.connect(
            "toggled",
            self.on_display_mode_changed,
            "left",
        )

        self.used_radio.connect(
            "toggled",
            self.on_display_mode_changed,
            "used",
        )

        display_row.pack_start(
            self.left_radio,
            False,
            False,
            0,
        )

        display_row.pack_start(
            self.used_radio,
            False,
            False,
            0,
        )

        refresh_label = Gtk.Label(
            label="Refresh",
        )

        refresh_label.set_margin_start(18)

        display_row.pack_start(
            refresh_label,
            False,
            False,
            0,
        )

        self.refresh_combo = Gtk.ComboBoxText()

        options = [
            (15, "15 seconds"),
            (30, "30 seconds"),
            (60, "1 minute"),
            (120, "2 minutes"),
            (300, "5 minutes"),
        ]

        known = False

        for seconds, label in options:
            self.refresh_combo.append(
                str(seconds),
                label,
            )

            if seconds == refresh_seconds:
                known = True

        if not known:
            self.refresh_combo.append(
                str(refresh_seconds),
                "{} seconds".format(
                    refresh_seconds
                ),
            )

        self.refresh_combo.set_active_id(
            str(refresh_seconds)
        )

        self.refresh_combo.connect(
            "changed",
            self.on_refresh_seconds_changed,
        )

        self.refresh_combo.set_size_request(
            160,
            -1,
        )

        display_row.pack_start(
            self.refresh_combo,
            False,
            False,
            0,
        )

        self.save_settings_button = Gtk.Button(
            label="Save changes"
        )

        self.save_settings_button.get_style_context().add_class(
            "suggested-action"
        )

        self.save_settings_button.set_sensitive(
            False
        )

        self.save_settings_button.connect(
            "clicked",
            self.on_save_settings,
        )

        display_row.pack_end(
            self.save_settings_button,
            False,
            False,
            0,
        )

        content.pack_start(
            display_row,
            False,
            False,
            0,
        )

        widget_title = Gtk.Label(
            xalign=0,
        )

        widget_title.set_markup(
            "<b>Widget</b>"
        )

        widget_title.set_margin_top(9)

        content.pack_start(
            widget_title,
            False,
            False,
            0,
        )

        widget_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )

        widget_row.set_margin_top(2)

        position_label = Gtk.Label(
            label="Position",
        )

        widget_row.pack_start(
            position_label,
            False,
            False,
            0,
        )

        self.position_combo = Gtk.ComboBoxText()

        position_options = [
            ("top-left", "Top left"),
            ("top-right", "Top right"),
            ("bottom-left", "Bottom left"),
            ("bottom-right", "Bottom right"),
        ]

        for value, label in position_options:
            self.position_combo.append(
                value,
                label,
            )

        if self._draft_widget_anchor not in {
            value
            for value, _label in position_options
        }:
            self._draft_widget_anchor = "top-right"

        self.position_combo.set_active_id(
            self._draft_widget_anchor
        )

        self.position_combo.connect(
            "changed",
            self.on_widget_anchor_changed,
        )

        self.position_combo.set_size_request(
            150,
            -1,
        )

        widget_row.pack_start(
            self.position_combo,
            False,
            False,
            0,
        )

        self.keep_visible_check = Gtk.CheckButton(
            label="Keep widget above other windows"
        )

        self.keep_visible_check.set_active(
            self._draft_widget_keep_visible
        )

        self.keep_visible_check.connect(
            "toggled",
            self.on_widget_keep_visible_changed,
        )

        widget_row.pack_start(
            self.keep_visible_check,
            False,
            False,
            10,
        )

        self.autostart_check = Gtk.CheckButton(
            label="Start automatically after login"
        )

        self.autostart_check.set_active(
            self._draft_widget_autostart
        )

        self.autostart_check.connect(
            "toggled",
            self.on_widget_autostart_changed,
        )

        widget_row.pack_start(
            self.autostart_check,
            False,
            False,
            0,
        )

        content.pack_start(
            widget_row,
            False,
            False,
            0,
        )

        self.status = Gtk.Label(
            label="",
            xalign=1,
        )

        self.status.set_margin_top(2)

        content.pack_start(
            self.status,
            False,
            False,
            0,
        )

        # ==================================================
        # FOOTER
        # ==================================================

        root.pack_start(
            Gtk.Separator(
                orientation=Gtk.Orientation.HORIZONTAL
            ),
            False,
            False,
            0,
        )

        footer = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
        )

        footer.set_margin_top(7)
        footer.set_margin_bottom(7)
        footer.set_margin_start(16)
        footer.set_margin_end(16)

        privacy = Gtk.Label(
            label=(
                "Credentials stay in provider profiles. "
                "NUNU does not store your password."
            ),
            xalign=0,
        )

        privacy.get_style_context().add_class(
            "dim-label"
        )

        footer.pack_start(
            privacy,
            True,
            True,
            0,
        )

        version = Gtk.Label(
            label="v0.2.0"
        )

        version.get_style_context().add_class(
            "dim-label"
        )

        footer.pack_end(
            version,
            False,
            False,
            0,
        )

        root.pack_end(
            footer,
            False,
            False,
            0,
        )


    def place_on_primary_monitor(self):
        display = Gdk.Display.get_default()

        if display is None:
            return False

        monitor = display.get_primary_monitor()

        if monitor is None:
            return False

        area = monitor.get_workarea()

        width, height = self.get_size()

        width = max(width, 1)
        height = max(height, 1)

        x = area.x + max(
            0,
            (area.width - width) // 2,
        )

        y = area.y + max(
            0,
            (area.height - height) // 2,
        )

        self.move(
            x,
            y,
        )

        return False


    def _active_monitor_names(self):
        try:
            result = subprocess.run(
                [
                    "xrandr",
                    "--listmonitors",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            names = []

            for line in result.stdout.splitlines()[1:]:
                parts = line.split()

                if not parts:
                    continue

                name = parts[-1].strip()

                if (
                    name
                    and name not in names
                ):
                    names.append(name)

            return names

        except Exception:
            return []


    def _refresh_monitor_combo(self):
        if not hasattr(
            self,
            "monitor_combo",
        ):
            return False

        self._updating_monitor_combo = True

        try:
            selected = (
                self._draft_widget_monitor
                or "primary"
            )

            self.monitor_combo.remove_all()

            self.monitor_combo.append(
                "primary",
                "Primary",
            )

            active_names = (
                self._active_monitor_names()
            )

            for name in active_names:
                self.monitor_combo.append(
                    name,
                    name,
                )

            if (
                selected != "primary"
                and selected not in active_names
            ):
                self.monitor_combo.append(
                    selected,
                    "{} (disconnected)".format(
                        selected
                    ),
                )

            self.monitor_combo.set_active_id(
                selected
            )

        finally:
            self._updating_monitor_combo = False

        return False


    def _on_monitors_changed(
        self,
        *args,
    ):
        GLib.idle_add(
            self.place_on_primary_monitor
        )

        if hasattr(
            self,
            "monitor_combo",
        ):
            GLib.idle_add(
                self._refresh_monitor_combo
            )


    def _mark_settings_dirty(self):
        self._settings_dirty = True

        if hasattr(
            self,
            "save_settings_button",
        ):
            self.save_settings_button.set_sensitive(
                True
            )

        self.status.set_text(
            "Unsaved display changes."
        )


    def on_display_mode_changed(
        self,
        button,
        mode,
    ):
        if not button.get_active():
            return

        self._draft_display_mode = mode
        self._mark_settings_dirty()


    def on_refresh_seconds_changed(
        self,
        combo,
    ):
        value = combo.get_active_id()

        if value is None:
            return

        self._draft_refresh_seconds = int(value)
        self._mark_settings_dirty()


    def on_widget_monitor_changed(
        self,
        combo,
    ):
        if self._updating_monitor_combo:
            return

        value = combo.get_active_id()

        if value is None:
            return

        self._draft_widget_monitor = value
        self._mark_settings_dirty()


    def on_widget_anchor_changed(
        self,
        combo,
    ):
        value = combo.get_active_id()

        if value is None:
            return

        self._draft_widget_anchor = value
        self._mark_settings_dirty()


    def on_widget_keep_visible_changed(
        self,
        button,
    ):
        self._draft_widget_keep_visible = (
            button.get_active()
        )
        self._mark_settings_dirty()


    def on_widget_autostart_changed(
        self,
        button,
    ):
        self._draft_widget_autostart = (
            button.get_active()
        )
        self._mark_settings_dirty()


    def _sync_widget_autostart(
        self,
        enabled,
    ):
        autostart_root = (
            Path.home()
            / ".config"
            / "autostart"
        )

        autostart_file = (
            autostart_root
            / "nunu-ai-usage-widget.desktop"
        )

        if not enabled:
            try:
                autostart_file.unlink()
            except FileNotFoundError:
                pass

            return

        autostart_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        launcher = (
            Path.home()
            / ".local"
            / "bin"
            / "nunu-ai-usage-widget"
        )

        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=NUNU AI Usage\n"
            "Comment=Monitor Codex and Claude usage quotas\n"
            f"Exec={launcher}\n"
            "Terminal=false\n"
            "Hidden=false\n"
            "StartupNotify=false\n"
        )

        temp = autostart_file.with_name(
            ".nunu-ai-usage-widget.desktop.tmp"
        )

        temp.write_text(
            content,
            encoding="utf-8",
        )

        temp.chmod(0o644)
        temp.replace(autostart_file)


    def on_save_settings(
        self,
        button,
    ):
        try:
            # Save exactly what the user currently sees
            # in the Desktop dropdowns.
            if hasattr(
                self,
                "monitor_combo",
            ):
                value = (
                    self.monitor_combo.get_active_id()
                )

                if value:
                    self._draft_widget_monitor = value

            if hasattr(
                self,
                "position_combo",
            ):
                value = (
                    self.position_combo.get_active_id()
                )

                if value:
                    self._draft_widget_anchor = value

            config = self.store.load()

            settings = config.setdefault(
                "settings",
                {},
            )

            settings["display_mode"] = (
                self._draft_display_mode
            )

            settings["refresh_seconds"] = (
                self._draft_refresh_seconds
            )

            widget_settings = settings.setdefault(
                "widget",
                {},
            )

            widget_settings["monitor"] = (
                self._draft_widget_monitor
            )

            widget_settings["anchor"] = (
                self._draft_widget_anchor
            )

            widget_settings["keep_visible"] = (
                self._draft_widget_keep_visible
            )

            widget_settings["autostart"] = (
                self._draft_widget_autostart
            )

            self.store.save(config)

            self._sync_widget_autostart(
                self._draft_widget_autostart
            )

            self._settings_dirty = False
            self.save_settings_button.set_sensitive(
                False
            )

            self.status.set_text(
                "✓ Settings saved. "
                "Widget settings updated."
            )

        except Exception as exc:
            self.status.set_text(
                "Could not save settings: {}".format(
                    exc
                )
            )


    def refresh_account_list(self):
        for child in self.account_list.get_children():
            self.account_list.remove(child)

        config = self.store.load()

        for account in config["accounts"]:
            row = ConfiguredAccountRow(
                account,
                self.on_account_action,
            )

            self.account_list.add(
                row
            )

        self.account_list.show_all()


    def on_account_action(
        self,
        action,
        account,
    ):
        account_id = account["id"]

        if action == "refresh":
            self.refresh_account_list()

            self.status.set_text(
                "✓ Account list refreshed."
            )
            return

        if action == "visibility":
            visible = not account.get(
                "show_on_widget",
                True,
            )

            self.store.set_account_visibility(
                account_id,
                visible,
            )

            self.refresh_account_list()

            self.status.set_text(
                "✓ {} {} on widget.".format(
                    account["label"],
                    "shown" if visible else "hidden",
                )
            )
            return

        if action == "rename":
            self._rename_configured_account(
                account
            )
            return

        if action == "reconnect":
            self._reconnect_configured_account(
                account
            )
            return

        if action == "remove":
            self._remove_configured_account(
                account
            )
            return


    def _reconnect_configured_account(
        self,
        account,
    ):
        provider_name = {
            "codex": "Codex",
            "claude": "Claude",
        }.get(
            account["provider"],
            account["provider"],
        )

        try:
            session = create_reconnect_session(
                account
            )

            runtime = start_login_runtime(
                session
            )

        except Exception as exc:
            self.status.set_text(
                "Could not reconnect {}: {}".format(
                    account["label"],
                    exc,
                )
            )
            return

        self.status.set_text(
            "Preparing {} reconnect…".format(
                account["label"]
            )
        )

        worker = threading.Thread(
            target=self._wait_for_login_challenge,
            args=(
                session,
                runtime,
                provider_name,
            ),
            daemon=True,
        )

        worker.start()


    def _rename_configured_account(
        self,
        account,
    ):
        dialog = Gtk.Dialog(
            title="Rename account",
            transient_for=self,
            modal=True,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Rename",
            Gtk.ResponseType.OK,
        )

        dialog.set_default_response(
            Gtk.ResponseType.OK
        )

        content = dialog.get_content_area()

        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_spacing(8)

        label = Gtk.Label(
            label="Local account label",
            xalign=0,
        )

        entry = Gtk.Entry()

        entry.set_text(
            account["label"]
        )

        entry.set_activates_default(
            True
        )

        content.pack_start(
            label,
            False,
            False,
            0,
        )

        content.pack_start(
            entry,
            False,
            False,
            0,
        )

        dialog.show_all()

        response = dialog.run()

        new_label = entry.get_text().strip()

        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return

        if not new_label:
            self.status.set_text(
                "Account name cannot be empty."
            )
            return

        self.store.rename_account(
            account["id"],
            new_label,
        )

        self.refresh_account_list()

        self.status.set_text(
            "✓ Account renamed to {}.".format(
                new_label
            )
        )


    def _remove_configured_account(
        self,
        account,
    ):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text="Remove {} from NUNU?".format(
                account["label"]
            ),
        )

        dialog.set_modal(True)

        connection_type = (
            account
            .get("connection", {})
            .get("type", "unknown")
        )

        if connection_type == "managed":
            secondary = (
                "This removes the account from NUNU only. "
                "Its isolated provider profile and credentials "
                "will not be deleted."
            )
        else:
            secondary = (
                "This removes the account from NUNU only. "
                "It will not sign out of the provider."
            )

        dialog.format_secondary_text(
            secondary
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Remove",
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return

        removed = self.store.remove_account(
            account["id"]
        )

        self.refresh_account_list()

        self.status.set_text(
            "✓ {} removed from NUNU.".format(
                removed["label"]
            )
        )


    def _ask_account_label(
        self,
        provider_name,
    ):
        dialog = Gtk.Dialog(
            title="Add {} account".format(provider_name),
            transient_for=self,
            modal=True,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Continue",
            Gtk.ResponseType.OK,
        )

        dialog.set_default_response(
            Gtk.ResponseType.OK
        )

        content = dialog.get_content_area()

        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_spacing(8)

        label = Gtk.Label(
            label="Local account label",
            xalign=0,
        )

        entry = Gtk.Entry()
        entry.set_text("Account")
        entry.set_activates_default(True)

        note = Gtk.Label(
            label=(
                "This name is only used inside NUNU. "
                "For example: Personal or Work."
            ),
            xalign=0,
        )

        note.set_line_wrap(True)
        note.get_style_context().add_class(
            "dim-label"
        )

        content.pack_start(
            label,
            False,
            False,
            0,
        )

        content.pack_start(
            entry,
            False,
            False,
            0,
        )

        content.pack_start(
            note,
            False,
            False,
            0,
        )

        dialog.show_all()

        response = dialog.run()

        value = entry.get_text().strip()

        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return None

        return value or "Account"


    def _safe_login_destination(
        self,
        url,
    ):
        try:
            parsed = urlsplit(url)

            return "{}://{}{}".format(
                parsed.scheme,
                parsed.netloc,
                parsed.path,
            )
        except Exception:
            return "Login link ready"


    def start_managed_sign_in(
        self,
        provider_id,
        provider_name,
    ):
        label = self._ask_account_label(
            provider_name
        )

        if label is None:
            return

        try:
            session = create_login_session(
                provider_id,
                label=label,
            )

            runtime = start_login_runtime(
                session
            )

        except Exception as exc:
            self.status.set_text(
                "Could not start {} sign-in: {}".format(
                    provider_name,
                    exc,
                )
            )
            return

        self.status.set_text(
            "Preparing {} sign-in…".format(
                provider_name
            )
        )

        worker = threading.Thread(
            target=self._wait_for_login_challenge,
            args=(
                session,
                runtime,
                provider_name,
            ),
            daemon=True,
        )

        worker.start()


    def _wait_for_login_challenge(
        self,
        session,
        runtime,
        provider_name,
    ):
        ok = False
        error = None

        try:
            ok = runtime.wait_for_challenge(
                timeout=30
            )
        except Exception as exc:
            error = str(exc)

        GLib.idle_add(
            self._finish_login_challenge,
            session,
            runtime,
            provider_name,
            ok,
            error,
        )


    def _finish_login_challenge(
        self,
        session,
        runtime,
        provider_name,
        ok,
        error,
    ):
        if not ok:
            runtime.terminate()

            message = (
                error
                or "No login link was received."
            )

            self.status.set_text(
                "Could not start {} sign-in: {}".format(
                    provider_name,
                    message,
                )
            )

            return False

        self._show_login_dialog(
            session,
            runtime,
            provider_name,
        )

        return False


    def _show_login_dialog(
        self,
        session,
        runtime,
        provider_name,
    ):
        COPY_LINK = 2001
        COPY_CODE = 2002
        OPEN_BROWSER = 2003

        dialog = Gtk.Dialog(
            title="Sign in to {}".format(
                provider_name
            ),
            transient_for=self,
            modal=True,
        )

        dialog.set_default_size(
            560,
            -1,
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Copy link",
            COPY_LINK,
        )

        if session.user_code:
            dialog.add_button(
                "Copy code",
                COPY_CODE,
            )

        dialog.add_button(
            "Open browser",
            OPEN_BROWSER,
        )

        verify_button = dialog.add_button(
            "Verify login",
            Gtk.ResponseType.OK,
        )

        verify_button.get_style_context().add_class(
            "suggested-action"
        )

        content = dialog.get_content_area()

        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.set_spacing(12)

        heading = Gtk.Label(
            xalign=0,
        )

        heading.set_markup(
            "<b>Complete sign-in in any browser</b>"
        )

        content.pack_start(
            heading,
            False,
            False,
            0,
        )

        destination = Gtk.Label(
            label=self._safe_login_destination(
                session.login_url
            ),
            xalign=0,
        )

        destination.set_selectable(True)

        content.pack_start(
            destination,
            False,
            False,
            0,
        )

        if session.user_code:
            code_title = Gtk.Label(
                label="Device code",
                xalign=0,
            )

            code_title.get_style_context().add_class(
                "dim-label"
            )

            code = Gtk.Label(
                label=session.user_code,
                xalign=0,
            )

            code.set_selectable(True)

            content.pack_start(
                code_title,
                False,
                False,
                0,
            )

            content.pack_start(
                code,
                False,
                False,
                0,
            )

        browser_note = Gtk.Label(
            label=(
                "Use Open browser, or Copy link and paste it "
                "into another Chrome profile, another browser, "
                "or another device."
            ),
            xalign=0,
        )

        browser_note.set_line_wrap(True)

        content.pack_start(
            browser_note,
            False,
            False,
            0,
        )

        warning = Gtk.Label(
            label=(
                "Anyone who completes this sign-in may connect "
                "their account to this NUNU profile. "
                "Only share the link intentionally."
            ),
            xalign=0,
        )

        warning.set_line_wrap(True)
        warning.get_style_context().add_class(
            "dim-label"
        )

        content.pack_start(
            warning,
            False,
            False,
            0,
        )

        result_label = Gtk.Label(
            label="",
            xalign=0,
        )

        result_label.set_line_wrap(True)

        content.pack_start(
            result_label,
            False,
            False,
            0,
        )

        clipboard = Gtk.Clipboard.get(
            Gdk.SELECTION_CLIPBOARD
        )

        dialog.show_all()

        while True:
            response = dialog.run()

            if response == COPY_LINK:
                clipboard.set_text(
                    session.login_url,
                    -1,
                )

                clipboard.store()

                result_label.set_text(
                    "✓ Login link copied."
                )

                dialog.show_all()
                continue

            if (
                response == COPY_CODE
                and session.user_code
            ):
                clipboard.set_text(
                    session.user_code,
                    -1,
                )

                clipboard.store()

                result_label.set_text(
                    "✓ Device code copied."
                )

                dialog.show_all()
                continue

            if response == OPEN_BROWSER:
                try:
                    Gtk.show_uri_on_window(
                        self,
                        session.login_url,
                        Gdk.CURRENT_TIME,
                    )

                    result_label.set_text(
                        "Browser opened. "
                        "Complete sign-in, then click Verify login."
                    )

                except Exception as exc:
                    result_label.set_text(
                        "Could not open browser: {}".format(
                            exc
                        )
                    )

                dialog.show_all()
                continue

            if response == Gtk.ResponseType.OK:
                try:
                    verified, message = (
                        verify_login_session(
                            session
                        )
                    )

                    if not verified:
                        result_label.set_text(
                            "Not connected yet. "
                            "Complete sign-in first, then try again. "
                            + str(message)
                        )

                        dialog.show_all()
                        continue

                    account, created = (
                        save_login_session(
                            session,
                            store=self.store,
                        )
                    )

                    runtime.terminate()
                    dialog.destroy()

                    if created:
                        self.status.set_text(
                            "✓ {} added as {}.".format(
                                provider_name,
                                account["label"],
                            )
                        )
                    else:
                        self.status.set_text(
                            "✓ This account is already in NUNU."
                        )

                    return

                except Exception as exc:
                    result_label.set_text(
                        "Verification failed: {}".format(
                            exc
                        )
                    )

                    dialog.show_all()
                    continue

            runtime.terminate()
            dialog.destroy()

            self.status.set_text(
                "{} sign-in cancelled.".format(
                    provider_name
                )
            )

            return


    def on_add_account(
        self,
        button,
        provider_id,
        provider_name,
    ):
        result = detect_existing_account(
            provider_id
        )

        if not result["authenticated"]:
            self.start_managed_sign_in(
                provider_id,
                provider_name,
            )
            return

        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text="Existing {} account detected".format(
                provider_name
            ),
        )

        dialog.set_modal(True)

        dialog.format_secondary_text(
            "This account is already signed in "
            "on this computer."
        )

        dialog.add_button(
            "Cancel",
            Gtk.ResponseType.CANCEL,
        )

        dialog.add_button(
            "Sign in another account",
            1001,
        )

        dialog.add_button(
            "Use this account",
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            try:
                account, created = use_existing_account(
                    provider_id,
                    store=self.store,
                )

                if created:
                    self.status.set_text(
                        "✓ {} added to NUNU.".format(
                            provider_name
                        )
                    )
                else:
                    self.status.set_text(
                        "✓ {} is already in NUNU.".format(
                            provider_name
                        )
                    )

            except Exception as exc:
                self.status.set_text(
                    "Could not add {}: {}".format(
                        provider_name,
                        exc,
                    )
                )

        elif response == 1001:
            self.start_managed_sign_in(
                provider_id,
                provider_name,
            )


def check():
    print("Account Manager: OK")
    print("GTK:", Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION)
    print("Providers: codex, claude")


def main():
    if "--check" in sys.argv:
        check()
        return

    window = AccountManager()

    window.show_all()

    GLib.idle_add(
        window.place_on_primary_monitor
    )

    Gtk.main()


if __name__ == "__main__":
    main()
