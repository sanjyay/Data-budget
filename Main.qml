import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import qs.Ui
import qs.Commons

Panel {
    id: root
    moduleName: "sanjyay.hotspot-budget"
    manageIpc: false
    property var shell: null
    readonly property var nativeTracker: shell ? shell.serviceFor(moduleName) : null
    readonly property var tracker: nativeTracker || bridge.item
    Loader {
        id: bridge
        active: !root.nativeTracker
        sourceComponent: TrackerBridge {}
    }
    readonly property var rows: tracker ? tracker.rows : []
    property string selectedUuid: ""
    property bool confirmForget: false
    readonly property var selected: {
        for (let i = 0; i < rows.length; i++) if (rows[i].uuid === selectedUuid) return rows[i]
        return null
    }
    readonly property var activeTracked: rows.filter(function(row) { return row.active && row.tracked })
    // Independent budgets must not average away a nearly exhausted connection.
    readonly property real budgetRatio: activeTracked.reduce(function(highest, row) {
        return Math.max(highest, row.budget > 0 ? (row.rx + row.tx) / row.budget : 0)
    }, 0)
    readonly property bool healthy: tracker && tracker.ready

    function bytes(value) {
        if (value >= 1000000000) return (value / 1000000000).toFixed(2) + " GB"
        return (value / 1000000).toFixed(1) + " MB"
    }
    function selectRow(index) {
        if (index < 0 || index >= rows.length) return
        selectedUuid = rows[index].uuid
        budget.text = String(rows[index].budget / 1000000)
        period.currentIndex = ["session", "daily", "monthly"].indexOf(rows[index].period)
        thresholds.text = rows[index].thresholds.join(", ")
        confirmForget = false
    }
    function save() {
        if (!selected || !healthy) return
        const values = thresholds.text.split(",").map(function(v) { return Number(v.trim()) })
        const amount = Number(budget.text)
        if (!isFinite(amount) || amount < 1 || amount > 1000000000 || values.length > 10 || values.some(function(v) { return !Number.isInteger(v) || v < 1 || v > 100 })) {
            tracker.notice = "Enter a positive MB budget and percentage thresholds from 1 to 100."
            return
        }
        tracker.send("configure", selectedUuid, amount, ["session", "daily", "monthly"][period.currentIndex], values)
    }
    onRowsChanged: {
        if (!selected && rows.length > 0) selectRow(0)
        else if (!rows.length) selectedUuid = ""
    }
    onOpenedChanged: if (opened) {
        for (let i = 0; i < rows.length; i++) if (rows[i].uuid === selectedUuid) { selectRow(i); break }
    }

    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    WidgetButton {
        id: button
        bar: root.bar
        hasVisualContent: true
        labelVisible: false
        fixedWidth: vertical ? barSize : Style.space(36)
        fixedHeight: vertical ? Style.space(32) : barSize
        active: !root.healthy || root.budgetRatio >= 1
        tooltipText: !root.healthy ? "Data Budget · " + (root.tracker ? root.tracker.error : "Starting tracker…")
            : !root.activeTracked.length ? "Data Budget · not tracking · click to set a budget"
            : "Data Budget" + (root.activeTracked.length > 1 ? " · icon shows the highest usage percentage" : "")
                + "\n" + root.activeTracked.map(function(row) {
                    return row.name + " · " + root.bytes(row.rx + row.tx) + " / " + root.bytes(row.budget)
                        + " (" + Math.floor(100 * (row.rx + row.tx) / row.budget) + "%)"
                }).join("\n")
        Accessible.name: tooltipText
        onPressed: function(mouseButton) { if (mouseButton === Qt.LeftButton) root.toggle() }

        Item {
            id: jar
            objectName: "budgetIcon"
            anchors.centerIn: parent
            width: Style.space(24)
            height: Style.space(24)
            opacity: root.healthy && !root.activeTracked.length ? 0.45 : 1
            property real fillLevel: root.healthy ? Math.min(1, Math.max(0, root.budgetRatio)) : 0
            readonly property color ink: !root.healthy ? button.activeColor : button.foreground
            readonly property color fillColor: root.budgetRatio >= 1 ? button.activeColor : Color.accent
            Behavior on fillLevel { NumberAnimation { duration: 350; easing.type: Easing.InOutQuad } }

            Canvas {
                id: glass
                anchors.fill: parent
                antialiasing: true
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                Connections {
                    target: jar
                    function onFillLevelChanged() { glass.requestPaint() }
                    function onInkChanged() { glass.requestPaint() }
                    function onFillColorChanged() { glass.requestPaint() }
                }
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.reset()
                    ctx.scale(width / 24, height / 24)
                    // Short neck, curved shoulders, and a softly rounded base.
                    ctx.beginPath()
                    ctx.moveTo(8, 5)
                    ctx.lineTo(16, 5)
                    ctx.lineTo(16, 6.5)
                    ctx.bezierCurveTo(16, 8, 19.5, 8.2, 19.5, 11.5)
                    ctx.lineTo(19.5, 18)
                    ctx.bezierCurveTo(19.5, 20.8, 17.8, 22, 15, 22)
                    ctx.lineTo(9, 22)
                    ctx.bezierCurveTo(6.2, 22, 4.5, 20.8, 4.5, 18)
                    ctx.lineTo(4.5, 11.5)
                    ctx.bezierCurveTo(4.5, 8.2, 8, 8, 8, 6.5)
                    ctx.closePath()
                    ctx.save()
                    ctx.clip()
                    if (jar.fillLevel > 0) {
                        const level = 22 - 17 * jar.fillLevel
                        const ripple = jar.fillLevel < 1 ? 0.5 : 0
                        ctx.fillStyle = jar.fillColor
                        ctx.beginPath()
                        ctx.moveTo(3, level)
                        ctx.bezierCurveTo(8, level - ripple, 14, level + ripple, 21, level)
                        ctx.lineTo(21, 24)
                        ctx.lineTo(3, 24)
                        ctx.closePath()
                        ctx.fill()
                    }
                    ctx.restore()
                    // Restore the silhouette after drawing the liquid path.
                    ctx.beginPath()
                    ctx.moveTo(8, 5); ctx.lineTo(16, 5); ctx.lineTo(16, 6.5)
                    ctx.bezierCurveTo(16, 8, 19.5, 8.2, 19.5, 11.5)
                    ctx.lineTo(19.5, 18)
                    ctx.bezierCurveTo(19.5, 20.8, 17.8, 22, 15, 22)
                    ctx.lineTo(9, 22)
                    ctx.bezierCurveTo(6.2, 22, 4.5, 20.8, 4.5, 18)
                    ctx.lineTo(4.5, 11.5)
                    ctx.bezierCurveTo(4.5, 8.2, 8, 8, 8, 6.5)
                    ctx.closePath()
                    ctx.strokeStyle = jar.ink
                    ctx.lineWidth = 1.25
                    ctx.lineJoin = "round"
                    ctx.stroke()
                    ctx.beginPath()
                    ctx.lineCap = "round"
                    ctx.lineWidth = 1.8
                    ctx.moveTo(8, 2.5); ctx.lineTo(16, 2.5)
                    ctx.stroke()
                }
            }
            Text {
                visible: !root.healthy
                anchors.centerIn: parent
                text: "!"
                color: jar.ink
                font.bold: true
                font.pixelSize: Style.space(13)
            }
        }
    }

    // Shared visual treatments keep focus, hover, and disabled states consistent.
    component Caption: Controls.Label {
        color: Qt.alpha(Color.foreground, 0.65)
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        textFormat: Text.PlainText
    }
    component Field: Controls.TextField {
        id: field
        implicitHeight: Style.space(38)
        color: Color.foreground
        selectionColor: Color.accent
        selectedTextColor: Color.background
        placeholderTextColor: Qt.alpha(Color.foreground, 0.4)
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        leftPadding: Style.space(12)
        rightPadding: Style.space(12)
        background: Rectangle {
            radius: Style.space(7)
            color: Qt.alpha(Color.foreground, 0.04)
            border.width: 1
            border.color: field.activeFocus ? Color.accent : Qt.alpha(Color.foreground, 0.14)
        }
    }
    component Select: Controls.ComboBox {
        id: select
        implicitHeight: Style.space(38)
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        palette.window: Color.background
        palette.base: Color.background
        palette.text: Color.foreground
        palette.buttonText: Color.foreground
        palette.highlight: Color.accent
        palette.highlightedText: Color.background
        opacity: enabled ? 1 : 0.45
        background: Rectangle {
            radius: Style.space(7)
            color: Qt.alpha(Color.foreground, select.hovered ? 0.08 : 0.04)
            border.width: 1
            border.color: select.activeFocus ? Color.accent : Qt.alpha(Color.foreground, 0.14)
        }
        contentItem: Text {
            text: select.displayText
            font: select.font
            color: Color.foreground
            textFormat: Text.PlainText
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            leftPadding: Style.space(12)
            rightPadding: Style.space(32)
        }
        indicator: Text {
            x: parent.width - width - Style.space(12)
            anchors.verticalCenter: parent.verticalCenter
            text: "⌄"
            color: Qt.alpha(Color.foreground, 0.65)
            font.pixelSize: Style.space(16)
        }
        delegate: Controls.ItemDelegate {
            required property string modelData
            required property int index
            width: select.width
            highlighted: select.highlightedIndex === index
            contentItem: Text {
                text: modelData
                font: select.font
                color: highlighted ? Color.background : Color.foreground
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            background: Rectangle { color: parent.highlighted ? Color.accent : Color.background }
        }
    }
    component Action: Controls.Button {
        id: action
        property bool primary: false
        property bool destructive: false
        implicitHeight: Style.space(38)
        horizontalPadding: Style.space(14)
        opacity: enabled ? 1 : 0.35
        contentItem: Text {
            text: action.text
            color: action.primary ? Color.background : action.destructive ? Color.urgent : Color.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            font.weight: action.primary ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            textFormat: Text.PlainText
        }
        background: Rectangle {
            radius: Style.space(7)
            color: action.primary ? Qt.alpha(Color.accent, action.down ? 0.75 : action.hovered ? 0.9 : 1)
                : Qt.alpha(Color.foreground, action.down ? 0.12 : action.hovered ? 0.08 : 0.03)
            border.width: 1
            border.color: action.activeFocus ? Color.accent : action.primary ? "transparent" : Qt.alpha(Color.foreground, 0.12)
        }
    }

    KeyboardPanel {
        id: popup
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        contentWidth: popup.fittedContentWidth(Style.space(360))
        contentHeight: popup.fittedContentHeight(content.implicitHeight)
        focusTarget: content

        Flickable {
            anchors.fill: parent
            contentHeight: content.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            Controls.ScrollBar.vertical: Controls.ScrollBar {}
            ColumnLayout {
                id: content
                objectName: "budgetContent"
                width: parent.width
                spacing: Style.space(16)
                focus: true
                Keys.onEscapePressed: root.close()

                RowLayout {
                    Layout.fillWidth: true
                    Controls.Label {
                        text: "Data Budget"
                        color: Color.foreground
                        font.family: Style.font.family
                        font.pixelSize: Style.space(19)
                        font.weight: Font.DemiBold
                        Layout.fillWidth: true
                    }
                    Rectangle {
                        implicitWidth: status.implicitWidth + Style.space(18)
                        implicitHeight: Style.space(24)
                        radius: height / 2
                        color: Qt.alpha(Color.accent, 0.12)
                        Caption {
                            id: status
                            anchors.centerIn: parent
                            color: Color.accent
                            text: !root.healthy ? "Unavailable" : !root.selected || !root.selected.tracked ? "Not tracking" : !root.selected.active ? "Offline" : "Tracking"
                        }
                    }
                }
                Controls.Label {
                    Layout.fillWidth: true
                    visible: !root.healthy
                    text: root.tracker ? root.tracker.error : "Tracker service unavailable."
                    color: Color.urgent
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                }
                Select {
                    id: connections
                    Layout.fillWidth: true
                    model: root.rows.map(function(row) { return row.name + (row.active ? "" : " · offline") })
                    currentIndex: {
                        for (let i = 0; i < root.rows.length; i++) if (root.rows[i].uuid === root.selectedUuid) return i
                        return -1
                    }
                    enabled: root.healthy && root.rows.length > 0
                    onActivated: function(index) { root.selectRow(index) }
                    Accessible.name: "Connection to track"
                }
                Controls.Label {
                    Layout.fillWidth: true
                    visible: !root.rows.length && root.healthy
                    text: "Connect to Wi-Fi or Ethernet to add a budget."
                    color: Color.foreground
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                }
                ColumnLayout {
                    visible: root.selected !== null
                    Layout.fillWidth: true
                    spacing: Style.space(16)
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Style.space(6)
                        RowLayout {
                            Layout.fillWidth: true
                            Caption { text: "DATA USED"; font.letterSpacing: 1; Layout.fillWidth: true }
                            Caption { text: root.selected ? root.selected.type + (root.selected.metered ? " · metered" : "") : "" }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Controls.Label {
                                text: root.selected ? root.bytes(root.selected.rx + root.selected.tx) : ""
                                color: Color.foreground
                                font.family: Style.font.family
                                font.pixelSize: Style.space(32)
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                            }
                            Caption {
                                text: root.selected ? Math.floor(100 * (root.selected.rx + root.selected.tx) / root.selected.budget) + "%" : ""
                                color: root.selected && root.selected.rx + root.selected.tx >= root.selected.budget ? Color.urgent : Color.accent
                                font.pixelSize: Style.space(18)
                            }
                        }
                        Caption { text: root.selected ? "of " + root.bytes(root.selected.budget) + " budget" : "" }
                        Controls.ProgressBar {
                            id: progress
                            Layout.fillWidth: true
                            Layout.topMargin: Style.space(6)
                            implicitHeight: Style.space(6)
                            value: root.selected ? Math.min(1, (root.selected.rx + root.selected.tx) / root.selected.budget) : 0
                            background: Rectangle { radius: height / 2; color: Qt.alpha(Color.foreground, 0.09) }
                            contentItem: Item {
                                Rectangle {
                                    width: parent.width * progress.position
                                    height: parent.height
                                    radius: height / 2
                                    color: progress.value >= 1 ? Color.urgent : Color.accent
                                    Behavior on width { NumberAnimation { duration: 300 } }
                                }
                            }
                            Accessible.name: "Budget used"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Repeater {
                            model: ["Downloaded", "Uploaded", "Remaining"]
                            ColumnLayout {
                                required property string modelData
                                required property int index
                                Layout.preferredWidth: content.width / 3
                                Layout.fillWidth: true
                                spacing: Style.space(4)
                                Caption { text: modelData }
                                Controls.Label {
                                    text: root.selected ? root.bytes(index === 0 ? root.selected.rx : index === 1 ? root.selected.tx : Math.max(0, root.selected.budget - root.selected.rx - root.selected.tx)) : ""
                                    color: Color.foreground
                                    font.family: Style.font.family
                                    font.pixelSize: Style.font.body
                                    font.weight: Font.Medium
                                }
                            }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Qt.alpha(Color.foreground, 0.1) }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Style.space(12)
                        rowSpacing: Style.space(8)
                        Caption { text: "Budget · MB" }
                        Caption { text: "Reset period" }
                        Field {
                            id: budget
                            Layout.preferredWidth: Style.space(100)
                            Layout.fillWidth: true
                            placeholderText: "1000"
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                            maximumLength: 16
                            Accessible.name: "Budget in megabytes, 1000 MB equals 1 GB"
                        }
                        Select {
                            id: period
                            Layout.preferredWidth: Style.space(190)
                            Layout.fillWidth: true
                            model: ["Each session", "Daily", "Monthly"]
                            Accessible.name: "Budget reset period"
                        }
                        Caption { text: "Alert thresholds · %"; Layout.columnSpan: 2 }
                        Field {
                            id: thresholds
                            Layout.fillWidth: true
                            Layout.columnSpan: 2
                            placeholderText: "50, 80, 100"
                            maximumLength: 48
                            Accessible.name: "Warning percentages, comma-separated"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Style.space(10)
                        Action {
                            Layout.fillWidth: true
                            primary: true
                            text: root.selected && root.selected.tracked ? "Save budget" : "Start tracking"
                            enabled: root.healthy
                            onClicked: root.save()
                        }
                        Action {
                            Layout.fillWidth: true
                            text: "Stop tracking"
                            enabled: root.healthy && root.selected && root.selected.tracked
                            onClicked: root.tracker.send("stop", root.selectedUuid, 0, "", [])
                        }
                    }
                    Action {
                        Layout.fillWidth: true
                        destructive: root.confirmForget
                        text: root.confirmForget ? "Confirm delete profile + totals" : "Forget saved profile"
                        enabled: root.healthy
                        onClicked: {
                            if (root.confirmForget) {
                                root.tracker.send("forget", root.selectedUuid, 0, "", [])
                                root.confirmForget = false
                            } else root.confirmForget = true
                        }
                    }
                }
                Controls.Label {
                    Layout.fillWidth: true
                    text: root.tracker ? root.tracker.notice : ""
                    visible: text !== "" && text !== "Saved."
                    color: Color.foreground
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    Accessible.role: Accessible.AlertMessage
                }
            }
        }
    }
}
