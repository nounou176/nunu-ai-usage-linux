const Main = imports.ui.main;
const GLib = imports.gi.GLib;
const ByteArray = imports.byteArray;
const Gio = imports.gi.Gio;
const Mainloop = imports.mainloop;
const St = imports.gi.St;
const Pango = imports.gi.Pango;
const Util = imports.misc.util;
const Desklet = imports.ui.desklet;

const CONTENT_WIDTH = 326;
const BAR_WIDTH = 282;

const BACKEND = GLib.build_filenamev([
    GLib.get_home_dir(),
    ".local",
    "bin",
    "nunu-ai-usage"
]);

const SETTINGS = GLib.build_filenamev([
    GLib.get_home_dir(),
    ".local",
    "bin",
    "nunu-ai-usage-settings"
]);

const CONFIG = GLib.build_filenamev([
    GLib.get_home_dir(),
    ".config",
    "nunu-ai-usage-linux",
    "config.json"
]);


function NunuAIUsageDesklet(metadata, deskletId) {
    this._init(metadata, deskletId);
}


NunuAIUsageDesklet.prototype = {
    __proto__: Desklet.Desklet.prototype,

    _init: function(metadata, deskletId) {
        Desklet.Desklet.prototype._init.call(
            this,
            metadata,
            deskletId
        );

        this._removed = false;
        this._refreshing = false;
        this._timer = null;
        this._configTimer = null;
        this._configStamp = null;
        this._root = null;
        this._refreshButton = null;
        this._refreshStatus = null;
        this._monitorChangedId = 0;
        this._placementTimer = 0;
        this._visibilityTimer = 0;

        this.metadata["prevent-decorations"] = true;
        this._updateDecoration();

        this._renderLoading();

        this._configStamp =
            this._getConfigStamp();

        this._startConfigWatcher();

        this._monitorChangedId =
            Main.layoutManager.connect(
                "monitors-changed",
                () => {
                    this._onMonitorsChanged();
                }
            );

        this._schedulePlacement(350);
        this._startVisibilityGuard();
        this._refresh();
    },


    _label: function(text, styleClass) {
        let label = new St.Label({
            text: String(text),
            style_class: styleClass
        });

        label.clutter_text.ellipsize =
            Pango.EllipsizeMode.NONE;

        return label;
    },


    _button: function(text, callback) {
        let button = new St.Button({
            label: text,
            reactive: true,
            can_focus: true,
            track_hover: true,
            style_class: "nau-icon-button"
        });

        button.connect(
            "clicked",
            callback
        );

        return button;
    },


    _setRoot: function(root) {
        if (this._root)
            this._root.destroy();

        this._root = root;
        this.setContent(root);
    },


    _makeRoot: function() {
        let root = new St.BoxLayout({
            vertical: true,
            width: CONTENT_WIDTH,
            style_class: "nau-root"
        });

        let card = new St.BoxLayout({
            vertical: true,
            width: CONTENT_WIDTH,
            style_class: "nau-card"
        });

        root.add(card);

        return [root, card];
    },


    _progress: function(percent) {
        let value = Number(percent);

        if (!Number.isFinite(value))
            value = 0;

        value = Math.max(
            0,
            Math.min(100, value)
        );

        let track = new St.BoxLayout({
            width: BAR_WIDTH,
            style_class: "nau-progress-track"
        });

        let fill = new St.Bin({
            width: Math.round(
                BAR_WIDTH * value / 100
            ),
            style_class: "nau-progress-fill"
        });

        track.add(fill);

        return track;
    },


    _normalizeReset: function(value) {
        if (!value)
            return null;

        let s = String(value);

        s = s.replace(/\u202f/g, " ");
        s = s.replace(
            /\(Asia\/Ho_Chi_Minh\)/gi,
            ""
        );

        s = s.replace(
            /^Resets\s*/i,
            ""
        );

        s = s.replace(
            /Sep(\d+)/g,
            "Sep $1"
        );

        s = s.replace(
            /,(\d)/g,
            ", $1"
        );

        s = s.replace(
            /(\d)(am|pm)\b/gi,
            "$1 $2"
        );

        s = s.trim();

        return s
            ? "Resets " + s
            : null;
    },


    _usageRow: function(window) {
        let box = new St.BoxLayout({
            vertical: true,
            style_class: "nau-limit"
        });

        let row = new St.BoxLayout({
            vertical: false,
            width: BAR_WIDTH
        });

        let name = this._label(
            window.name || "Limit",
            "nau-limit-title"
        );

        name.x_expand = true;

        row.add(name);

        row.add(
            this._label(
                String(window.display_percent) +
                "% " +
                String(window.display_suffix),
                "nau-percent"
            )
        );

        box.add(row);

        box.add(
            this._progress(
                window.display_percent
            )
        );

        let resetText =
            this._normalizeReset(
                window.reset_text
            );

        if (resetText) {
            box.add(
                this._label(
                    resetText,
                    "nau-reset"
                )
            );
        }

        return box;
    },


    _provider: function(account) {
        let box = new St.BoxLayout({
            vertical: true,
            style_class: "nau-provider"
        });

        let headingText =
            String(account.provider_name || "") +
            " · " +
            String(account.label || "Account");

        box.add(
            this._label(
                headingText,
                "nau-provider-heading"
            )
        );

        if (!account.ok) {
            box.add(
                this._label(
                    "Needs reconnect",
                    "nau-unavailable"
                )
            );

            return box;
        }

        for (let window of account.windows || [])
            box.add(this._usageRow(window));

        return box;
    },


    _formatInterval: function(seconds) {
        let value = Number(seconds);

        if (value >= 60 &&
            value % 60 === 0)
            return (value / 60) + "m";

        return value + "s";
    },


    _renderLoading: function() {
        let [root, card] = this._makeRoot();

        card.add(
            this._label(
                "NUNU AI Usage",
                "nau-main-title"
            )
        );

        card.add(
            this._label(
                "Loading usage…",
                "nau-muted"
            )
        );

        this._setRoot(root);
    },


    _render: function(data) {
        let [root, card] = this._makeRoot();

        let titleRow = new St.BoxLayout({
            vertical: false,
            width: BAR_WIDTH,
            style_class: "nau-title-row"
        });

        let title = this._label(
            "NUNU AI Usage",
            "nau-main-title"
        );

        title.x_expand = true;
        titleRow.add(title);

        this._refreshButton =
            this._button(
                "↻",
                () => this._refresh()
            );

        titleRow.add(
            this._refreshButton
        );

        titleRow.add(
            this._button(
                "⚙",
                () => Util.spawnCommandLine(
                    SETTINGS
                )
            )
        );

        card.add(titleRow);

        this._refreshStatus =
            this._label(
                "",
                "nau-refresh-status"
            );

        card.add(
            this._refreshStatus
        );

        let accounts = data.accounts || [];

        if (accounts.length === 0) {
            card.add(
                this._label(
                    "No accounts selected for display.",
                    "nau-muted"
                )
            );
        }

        accounts.forEach(
            (account, index) => {
                card.add(
                    this._provider(account)
                );

                if (index < accounts.length - 1) {
                    card.add(
                        new St.Widget({
                            height: 1,
                            width: BAR_WIDTH,
                            style_class: "nau-divider"
                        })
                    );
                }
            }
        );

        let now = new Date();

        card.add(
            this._label(
                "Updated " +
                now.toLocaleTimeString(
                    [],
                    {
                        hour: "numeric",
                        minute: "2-digit"
                    }
                ) +
                " · " +
                this._formatInterval(
                    data.refresh_seconds || 60
                ),
                "nau-footer"
            )
        );

        this._setRoot(root);

        this._scheduleRefresh(
            data.refresh_seconds || 60
        );
    },


    _renderError: function(message) {
        let [root, card] = this._makeRoot();

        card.add(
            this._label(
                "NUNU AI Usage",
                "nau-main-title"
            )
        );

        card.add(
            this._label(
                "Usage unavailable",
                "nau-error"
            )
        );

        card.add(
            this._label(
                String(message || ""),
                "nau-muted"
            )
        );

        this._setRoot(root);
        this._scheduleRefresh(60);
    },


    _getConfigStamp: function() {
        try {
            let file = Gio.File.new_for_path(
                CONFIG
            );

            let info = file.query_info(
                "time::modified,time::modified-usec",
                Gio.FileQueryInfoFlags.NONE,
                null
            );

            return (
                String(
                    info.get_attribute_uint64(
                        "time::modified"
                    )
                )
                + ":"
                + String(
                    info.get_attribute_uint32(
                        "time::modified-usec"
                    )
                )
            );

        } catch (error) {
            return null;
        }
    },


    _startConfigWatcher: function() {
        if (this._configTimer)
            return;

        this._configTimer =
            Mainloop.timeout_add_seconds(
                1,
                () => {
                    if (this._removed)
                        return false;

                    let stamp =
                        this._getConfigStamp();

                    if (
                        stamp &&
                        this._configStamp &&
                        stamp !== this._configStamp
                    ) {
                        if (!this._refreshing) {
                            this._configStamp =
                                stamp;

                            this._setRefreshingState(
                                true
                            );

                            this._schedulePlacement(
                                100
                            );

                            this._refresh();
                        }
                    } else if (
                        stamp &&
                        !this._configStamp
                    ) {
                        this._configStamp =
                            stamp;
                    }

                    return true;
                }
            );
    },


    _scheduleRefresh: function(seconds) {
        if (this._timer) {
            Mainloop.source_remove(
                this._timer
            );
            this._timer = null;
        }

        let interval = Math.max(
            15,
            Number(seconds) || 60
        );

        this._timer =
            Mainloop.timeout_add_seconds(
                interval,
                () => {
                    if (this._removed)
                        return false;

                    this._refresh();

                    return true;
                }
            );
    },


    _setRefreshingState: function(active) {
        if (this._refreshButton) {
            this._refreshButton.set_label(
                active ? "…" : "↻"
            );
        }

        if (this._refreshStatus) {
            this._refreshStatus.set_text(
                active
                    ? "Refreshing…"
                    : ""
            );
        }
    },


    _refresh: function() {
        if (this._refreshing ||
            this._removed)
            return;

        this._refreshing = true;

        this._setRefreshingState(
            true
        );

        Util.spawnCommandLineAsyncIO(
            null,
            (stdout, stderr, exitCode) => {
                this._refreshing = false;

                if (this._removed)
                    return;

                this._setRefreshingState(
                    false
                );

                try {
                    if (exitCode !== 0)
                        throw new Error(
                            stderr ||
                            "Backend exit " +
                            exitCode
                        );

                    this._render(
                        JSON.parse(
                            stdout || "{}"
                        )
                    );

                } catch (error) {
                    global.logError(
                        "NUNU AI Usage Linux: " +
                        (error.message || error)
                    );

                    this._renderError(
                        error.message || error
                    );
                }
            },
            {
                argv: [BACKEND]
            }
        );
    },


    _readPlacementConfig: function() {
        let fallback = {
            monitor: "primary",
            anchor: "top-right",
            margin_x: 32,
            margin_y: 32,
            keep_visible: true
        };

        try {
            let path =
                GLib.get_home_dir()
                + "/.config/nunu-ai-usage-linux/config.json";

            let result =
                GLib.file_get_contents(path);

            if (!result[0])
                return fallback;

            let data =
                JSON.parse(
                    ByteArray.toString(result[1])
                );

            let widget =
                data.settings
                && data.settings.widget
                    ? data.settings.widget
                    : {};

            return {
                monitor:
                    typeof widget.monitor === "string"
                        ? widget.monitor
                        : fallback.monitor,

                anchor:
                    typeof widget.anchor === "string"
                        ? widget.anchor
                        : fallback.anchor,

                margin_x:
                    Math.max(
                        0,
                        Number(widget.margin_x) || 0
                    ),

                margin_y:
                    Math.max(
                        0,
                        Number(widget.margin_y) || 0
                    ),

                keep_visible:
                    widget.keep_visible !== false
            };
        } catch (error) {
            global.logError(
                "NUNU placement config: "
                + (error.message || error)
            );

            return fallback;
        }
    },


    _xrandrMonitorGeometry: function(
        connector
    ) {
        try {
            let result =
                GLib.spawn_command_line_sync(
                    "xrandr --listmonitors"
                );

            if (!result[0])
                return null;

            let output =
                ByteArray.toString(
                    result[1]
                );

            let lines =
                output.split("\n");

            for (
                let i = 0;
                i < lines.length;
                i++
            ) {
                let line =
                    lines[i].trim();

                if (!line)
                    continue;

                let parts =
                    line.split(/\s+/);

                if (
                    parts.length < 3
                    || parts[
                        parts.length - 1
                    ] !== connector
                ) {
                    continue;
                }

                let match =
                    line.match(
                        /(\d+)\/\d+x(\d+)\/\d+([+-]\d+)([+-]\d+)\s+\S+\s*$/
                    );

                if (!match)
                    continue;

                return {
                    width: Number(match[1]),
                    height: Number(match[2]),
                    x: Number(match[3]),
                    y: Number(match[4])
                };
            }
        } catch (error) {
            global.logError(
                "NUNU xrandr monitor map: "
                + (error.message || error)
            );
        }

        return null;
    },


    _resolveTargetMonitor: function(config) {
        let monitors =
            Main.layoutManager.monitors || [];

        if (monitors.length === 0)
            return null;

        if (
            !config.monitor
            || config.monitor === "primary"
        ) {
            return (
                Main.layoutManager.primaryMonitor
                || monitors[0]
            );
        }

        // First allow a native Cinnamon monitor name.
        for (
            let i = 0;
            i < monitors.length;
            i++
        ) {
            if (
                monitors[i].name
                === config.monitor
            ) {
                return monitors[i];
            }
        }

        // NUNU Settings stores the Linux/XRandR
        // connector name: eDP, HDMI-A-0, DP-1-0...
        //
        // Cinnamon exposes human-readable names instead,
        // and its monitor indexes may use a different order.
        // Match the two APIs by physical geometry.
        let geometry =
            this._xrandrMonitorGeometry(
                config.monitor
            );

        if (geometry) {
            for (
                let i = 0;
                i < monitors.length;
                i++
            ) {
                let monitor =
                    monitors[i];

                if (
                    monitor.x === geometry.x
                    && monitor.y === geometry.y
                    && monitor.width
                        === geometry.width
                    && monitor.height
                        === geometry.height
                ) {
                    return monitor;
                }
            }
        }

        // Selected monitor is unavailable.
        // keep_visible=true means temporarily use Primary.
        if (config.keep_visible) {
            return (
                Main.layoutManager.primaryMonitor
                || monitors[0]
            );
        }

        return null;
    },


    _applyPlacement: function() {
        if (
            this._removed
            || !this.actor
        ) {
            return false;
        }

        let config =
            this._readPlacementConfig();

        let monitor =
            this._resolveTargetMonitor(config);

        if (!monitor)
            return false;

        let size =
            this.actor.get_transformed_size();

        let width =
            Number(size[0]) || 0;

        let height =
            Number(size[1]) || 0;

        if (
            width < 20
            || height < 20
        ) {
            return false;
        }

        let right =
            config.anchor.indexOf("right")
            !== -1;

        let bottom =
            config.anchor.indexOf("bottom")
            !== -1;

        let x =
            right
                ? monitor.x
                  + monitor.width
                  - width
                  - config.margin_x
                : monitor.x
                  + config.margin_x;

        let y =
            bottom
                ? monitor.y
                  + monitor.height
                  - height
                  - config.margin_y
                : monitor.y
                  + config.margin_y;

        x = Math.max(
            monitor.x,
            Math.min(
                x,
                monitor.x
                + monitor.width
                - width
            )
        );

        y = Math.max(
            monitor.y,
            Math.min(
                y,
                monitor.y
                + monitor.height
                - height
            )
        );

        x = Math.round(x);
        y = Math.round(y);

        this.actor.set_position(
            x,
            y
        );

        this._persistPosition(
            x,
            y
        );

        return false;
    },


    _schedulePlacement: function(delay) {
        if (this._removed)
            return;

        if (this._placementTimer) {
            Mainloop.source_remove(
                this._placementTimer
            );
        }

        this._placementTimer =
            Mainloop.timeout_add(
                delay || 100,
                () => {
                    this._placementTimer = 0;
                    return this._applyPlacement();
                }
            );
    },


    _persistPosition: function(x, y) {
        try {
            let key = "enabled-desklets";

            let items =
                global.settings.get_strv(key);

            let prefix =
                this._uuid
                + ":"
                + this.instance_id
                + ":";

            for (
                let i = 0;
                i < items.length;
                i++
            ) {
                if (
                    items[i].indexOf(prefix)
                    !== 0
                ) {
                    continue;
                }

                let parts =
                    items[i].split(":");

                if (parts.length < 4)
                    return;

                let newX =
                    String(Math.round(x));

                let newY =
                    String(Math.round(y));

                if (
                    parts[2] === newX
                    && parts[3] === newY
                ) {
                    return;
                }

                parts[2] = newX;
                parts[3] = newY;

                items[i] =
                    parts.join(":");

                global.settings.set_strv(
                    key,
                    items
                );

                return;
            }
        } catch (error) {
            global.logError(
                "NUNU position persistence: "
                + (error.message || error)
            );
        }
    },


    _getActorRect: function() {
        let position =
            this.actor.get_transformed_position();

        let size =
            this.actor.get_transformed_size();

        return {
            x: Number(position[0]) || 0,
            y: Number(position[1]) || 0,
            width: Number(size[0]) || 0,
            height: Number(size[1]) || 0
        };
    },


    _isFullyInsideAnyMonitor: function() {
        let rect =
            this._getActorRect();

        if (
            rect.width < 1
            || rect.height < 1
        ) {
            return true;
        }

        let monitors =
            Main.layoutManager.monitors || [];

        for (
            let i = 0;
            i < monitors.length;
            i++
        ) {
            let monitor =
                monitors[i];

            let inside =
                rect.x >= monitor.x
                && rect.y >= monitor.y
                && (
                    rect.x + rect.width
                ) <= (
                    monitor.x + monitor.width
                )
                && (
                    rect.y + rect.height
                ) <= (
                    monitor.y + monitor.height
                );

            if (inside)
                return true;
        }

        return false;
    },


    _ensureVisible: function() {
        if (
            this._removed
            || !this.actor
        ) {
            return;
        }

        let config =
            this._readPlacementConfig();

        if (!config.keep_visible)
            return;

        if (
            !this._isFullyInsideAnyMonitor()
        ) {
            this._schedulePlacement(100);
        }
    },


    _startVisibilityGuard: function() {
        if (this._visibilityTimer)
            return;

        this._visibilityTimer =
            Mainloop.timeout_add_seconds(
                3,
                () => {
                    if (this._removed) {
                        this._visibilityTimer = 0;
                        return false;
                    }

                    this._ensureVisible();

                    return true;
                }
            );
    },


    _onMonitorsChanged: function() {
        if (this._removed)
            return;

        this._schedulePlacement(250);
    },


    on_desklet_removed: function() {
        if (this._monitorChangedId) {
            try {
                Main.layoutManager.disconnect(
                    this._monitorChangedId
                );
            } catch (error) {
            }

            this._monitorChangedId = 0;
        }

        this._removed = true;

        if (this._placementTimer) {
            Mainloop.source_remove(
                this._placementTimer
            );

            this._placementTimer = 0;
        }

        if (this._visibilityTimer) {
            Mainloop.source_remove(
                this._visibilityTimer
            );

            this._visibilityTimer = 0;
        }

        if (this._timer) {
            Mainloop.source_remove(
                this._timer
            );

            this._timer = null;
        }
    }
};


function main(metadata, deskletId) {
    return new NunuAIUsageDesklet(
        metadata,
        deskletId
    );
}
