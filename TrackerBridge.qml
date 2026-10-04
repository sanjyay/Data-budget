import QtQuick
import Quickshell.Io

// Replacement bars receive a service-less facade. This narrow, local IPC
// interface exposes only this plugin's own public budget view and actions.
Item {
    id: root
    property var rows: []
    property string error: "Connecting to tracker…"
    property string notice: ""
    property bool ready: false
    property bool received: false

    function refresh() {
        if (!query.running) {
            received = false
            query.running = true
        }
    }
    function send(action, uuid, budget, period, thresholds) {
        if (!ready || request.running) return
        const payload = JSON.stringify({action: action, uuid: uuid,
            budget_mb: budget, period: period, thresholds: thresholds})
        if (payload.length > 8192) return
        notice = "Saving…"
        request.command = ["omarchy-shell", "sanjyay.hotspot-budget.tracker", "submit", payload]
        request.running = true
    }
    Process {
        id: query
        command: ["omarchy-shell", "sanjyay.hotspot-budget.tracker", "snapshot"]
        stdout: SplitParser {
            onRead: function(line) {
                if (line.length > 131072) return
                try {
                    const value = JSON.parse(line)
                    if (!Array.isArray(value.rows) || value.rows.length > 96) return
                    root.rows = value.rows
                    root.error = String(value.error || "")
                    root.notice = String(value.notice || "")
                    root.ready = value.ready === true
                    root.received = true
                } catch (_) { }
            }
        }
        onExited: function(exitCode) {
            if (exitCode !== 0 || !root.received) {
                root.ready = false
                root.error = "Tracker unavailable. Check that Data Budget is enabled."
            }
        }
    }
    Process {
        id: request
        onExited: function(exitCode) {
            if (exitCode !== 0) root.notice = "Could not send settings. Please retry."
            root.refresh()
        }
    }
    Timer {
        interval: 2000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }
    Component.onDestruction: { query.running = false; request.running = false }
}
