import QtQuick
import Quickshell.Io

Item {
    id: root
    property var shell: null
    property var rows: []
    property string error: "Starting tracker…"
    property string notice: ""
    property bool ready: false
    property bool stopping: false
    property int failures: 0
    property double lastMessage: 0

    function send(action, uuid, budget, period, thresholds) {
        if (!ready || !worker.running) return
        notice = "Saving…"
        worker.write(JSON.stringify({action: action, uuid: uuid,
            budget_mb: budget, period: period, thresholds: thresholds}) + "\n")
    }

    IpcHandler {
        target: "sanjyay.hotspot-budget.tracker"
        function snapshot(): string {
            return JSON.stringify({rows: root.rows, error: root.error, notice: root.notice, ready: root.ready})
        }
        function submit(payload: string): bool {
            if (!root.ready || payload.length > 8192) return false
            try {
                const value = JSON.parse(payload)
                if (!["configure", "stop", "forget"].includes(value.action) || typeof value.uuid !== "string") return false
                root.send(value.action, value.uuid, value.budget_mb, value.period, value.thresholds)
                return true
            } catch (_) { return false }
        }
    }

    Process {
        id: worker
        command: ["/usr/bin/python3", "-B", "-u", decodeURIComponent(Qt.resolvedUrl("scripts/tracker.py").toString().replace(/^file:\/\//, ""))]
        stdinEnabled: true
        onStarted: root.lastMessage = Date.now()
        stdout: SplitParser {
            onRead: function(data) {
                if (data.length > 131072) { worker.running = false; return }
                try {
                    const value = JSON.parse(data)
                    if (!Array.isArray(value.rows) || value.rows.length > 96) return
                    root.rows = value.rows
                    root.error = String(value.error || "")
                    root.notice = String(value.notice || "")
                    root.ready = !root.error
                    root.lastMessage = Date.now()
                    if (root.ready) root.failures = 0
                } catch (_) {
                    root.error = "Invalid tracker response."
                    root.ready = false
                }
            }
        }
        onExited: {
            root.ready = false
            root.rows = []
            if (!root.error) root.error = "Tracker stopped. Retrying…"
            if (!root.stopping) {
                root.failures = Math.min(root.failures + 1, 5)
                retry.interval = Math.min(30000, 1000 * Math.pow(2, root.failures))
                retry.restart()
            }
        }
    }
    Timer {
        id: retry
        onTriggered: worker.running = true
    }
    Timer {
        interval: 3000
        running: true
        repeat: true
        onTriggered: {
            if (worker.running && root.lastMessage > 0 && Date.now() - root.lastMessage > 12000) {
                root.ready = false
                root.error = "Tracker is not responding. Restarting…"
                worker.running = false
            }
        }
    }
    Component.onCompleted: { lastMessage = Date.now(); worker.running = true }
    Component.onDestruction: { stopping = true; retry.stop(); worker.running = false }
}
