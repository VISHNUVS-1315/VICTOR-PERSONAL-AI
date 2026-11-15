import QtQuick
import QtQuick.Window

// VICTOR HUD - frameless, animated, state-reactive.
// Visual language: one reactor core, one waveform ring, one transcript.
// No panels, no notification chrome, no emoji.
Window {
    id: root
    width: 980
    height: 680
    visible: victor.hudVisible
    color: "transparent"
    title: "VICTOR"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint

    // ---------------------------------------------------------------- theme
    readonly property color bgTop: "#07101d"
    readonly property color bgBottom: "#03060b"

    readonly property string st: victor.systemState
    readonly property color accent: {
        switch (st) {
        case "listening": return "#6ef3b0"
        case "thinking":  return "#ffc46b"
        case "speaking":  return "#9dbcff"
        case "sleeping":  return "#64748b"
        case "offline":   return "#ff7a7a"
        default:          return "#4fd1ff"
        }
    }

    // Animation driver. Everything that moves is derived from `phase`/`spin`,
    // which advance on this timer (14 fps idle, 25 fps active). There are no
    // independent 60 fps animations, so an idle HUD costs almost nothing.
    property real phase: 0.0
    property real spin: 0.0
    property real amp: {
        switch (st) {
        case "listening": return 0.18 + victor.audioLevel * 0.82
        case "speaking":  return 0.30 + victor.audioLevel * 0.70
        case "thinking":  return 0.26
        default:          return 0.09
        }
    }

    Timer {
        interval: (st === "idle" || st === "sleeping") ? 70 : 40
        running: root.visible
        repeat: true
        onTriggered: {
            root.phase += 0.11
            root.spin = (root.spin + (root.st === "thinking" ? 2.6 : 0.9)) % 360
        }
    }

    // QA hook: setting a path renders the current frame to that file.
    // Used by run_victor.py --capture, harmless in normal use.
    property string capturePath: ""
    onCapturePathChanged: {
        if (capturePath.length > 0) {
            shell.grabToImage(function (result) {
                if (result.saveToFile(capturePath))
                    console.log("CAPTURED " + capturePath)
            })
        }
    }

    Shortcut {
        sequence: "Escape"
        onActivated: victor.interrupt()
    }

    // ---------------------------------------------------------------- shell
    Rectangle {
        id: shell
        anchors.fill: parent
        radius: 22
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.bgTop }
            GradientStop { position: 1.0; color: root.bgBottom }
        }
        border.width: 1
        border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.22)

        // Static light pool behind the core
        Rectangle {
            width: 620; height: 620; radius: 310
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -24
            color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.045)
        }

        // ------------------------------------------------------------ header
        Item {
            id: header
            height: 62
            anchors { left: parent.left; right: parent.right; top: parent.top }
            anchors.leftMargin: 26
            anchors.rightMargin: 26

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                onPressed: root.startSystemMove()
            }

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    text: "VICTOR"
                    color: "#d8ecff"
                    font.family: "Segoe UI"
                    font.pixelSize: 17
                    font.bold: true
                    font.letterSpacing: 7
                }
                Text {
                    text: "PERSONAL AI"
                    color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.55)
                    font.family: "Consolas"
                    font.pixelSize: 9
                    font.letterSpacing: 3
                }
            }

            Text {
                text: "CLOSE"
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                color: closeHover.containsMouse ? "#e6f2ff" : "#4a6b85"
                font.family: "Consolas"
                font.pixelSize: 10
                font.letterSpacing: 2
                MouseArea {
                    id: closeHover
                    anchors.fill: parent
                    anchors.margins: -10
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: victor.quitApp()
                }
            }
        }

        // --------------------------------------------------------------- core
        Item {
            id: coreArea
            width: 400
            height: 400
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: header.bottom
            anchors.topMargin: 14

            readonly property real cx: width / 2
            readonly property real cy: height / 2

            // Outer tick ring (48 marks, every 4th longer)
            Repeater {
                model: 48
                Item {
                    width: 2
                    height: 188
                    x: coreArea.cx - width / 2
                    y: coreArea.cy - height
                    transformOrigin: Item.Bottom
                    rotation: index * 7.5
                    Rectangle {
                        anchors.top: parent.top
                        width: index % 4 === 0 ? 2 : 1
                        height: index % 4 === 0 ? 10 : 5
                        color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b,
                                       index % 4 === 0 ? 0.45 : 0.18)
                    }
                }
            }

            // Ring 1 with a slow scanner
            Rectangle {
                width: 330; height: 330
                radius: width / 2
                anchors.centerIn: parent
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.20)
            }
            Item {
                width: 6; height: 165
                x: coreArea.cx - width / 2
                y: coreArea.cy - height
                transformOrigin: Item.Bottom
                rotation: root.spin
                Rectangle {
                    anchors.top: parent.top
                    width: 6; height: 6; radius: 3
                    color: root.accent
                }
            }

            // Ring 2, counter-rotating pair
            Rectangle {
                width: 268; height: 268
                radius: width / 2
                anchors.centerIn: parent
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.13)
            }
            Repeater {
                model: 2
                Item {
                    width: 4
                    height: 134
                    x: coreArea.cx - width / 2
                    y: coreArea.cy - height
                    transformOrigin: Item.Bottom
                    rotation: index * 180 - root.spin * 0.75
                    Rectangle {
                        anchors.top: parent.top
                        width: 4; height: 4; radius: 2
                        color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.85)
                    }
                }
            }

            // Waveform ring - radius 107, bars grow outward to 151
            Repeater {
                model: 64
                Item {
                    id: barSlot
                    readonly property real shape: Math.min(
                        1.0,
                        root.amp * (0.30 + 0.85 * Math.abs(Math.sin(root.phase + index * 0.42)))
                    )
                    width: 2
                    height: 107 + 44 * shape
                    x: coreArea.cx - width / 2
                    y: coreArea.cy - height
                    transformOrigin: Item.Bottom
                    rotation: index * 5.625
                    Rectangle {
                        anchors.top: parent.top
                        width: 2
                        height: 44 * barSlot.shape
                        radius: 1
                        color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b,
                                       0.30 + 0.60 * barSlot.shape)
                    }
                }
            }

            // Glow + reactor core
            Rectangle {
                width: 190; height: 190; radius: 95
                anchors.centerIn: parent
                color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.06)
                scale: 1.0 + root.amp * 0.10
            }
            Rectangle {
                width: 128; height: 128; radius: 64
                anchors.centerIn: parent
                color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.14)
                scale: 1.0 + root.amp * 0.12
            }
            Rectangle {
                width: 86; height: 86; radius: 43
                anchors.centerIn: parent
                color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.85)
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, 0.35)
            }
            Rectangle {
                width: 34; height: 34; radius: 17
                anchors.centerIn: parent
                color: Qt.rgba(1, 1, 1, 0.55 + 0.35 * root.amp)
            }

            // Click anywhere on the core to start, or to interrupt
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (victor.sessionActive)
                        victor.interrupt()
                    else
                        victor.startSession()
                }
            }
        }

        // ------------------------------------------------------------- status
        Column {
            id: statusBlock
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: coreArea.bottom
            anchors.topMargin: 4
            spacing: 10

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: victor.statusText
                color: root.accent
                font.family: "Consolas"
                font.pixelSize: 11
                font.letterSpacing: 4
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 240; height: 1
                color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.18)
            }
        }

        // --------------------------------------------------------- transcript
        ListView {
            id: transcript
            anchors {
                left: parent.left
                right: parent.right
                top: statusBlock.bottom
                bottom: footer.top
                leftMargin: 60
                rightMargin: 60
                topMargin: 20
                bottomMargin: 6
            }
            clip: true
            spacing: 12
            model: ListModel { id: transcriptModel }

            delegate: Item {
                width: transcript.width
                height: bodyText.implicitHeight + 2

                Text {
                    id: roleLabel
                    width: 72
                    text: model.role
                    color: model.role === "YOU"
                           ? Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.72)
                           : "#7f93a8"
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.letterSpacing: 2
                }
                Text {
                    id: bodyText
                    anchors.left: roleLabel.right
                    width: transcript.width - roleLabel.width
                    text: model.body
                    wrapMode: Text.Wrap
                    color: model.role === "YOU" ? "#e8f4ff" : "#b9cfe4"
                    font.family: "Segoe UI"
                    font.pixelSize: 14
                }
            }

            Text {
                anchors.centerIn: parent
                visible: transcriptModel.count === 0
                text: "Say something to begin."
                color: "#3f5a72"
                font.family: "Segoe UI"
                font.pixelSize: 13
            }

            onCountChanged: positionViewAtEnd()
        }

        Connections {
            target: victor
            function onMessageAdded(role, text, stamp) {
                transcriptModel.append({ "role": role, "body": text, "stamp": stamp })
                while (transcriptModel.count > 40)
                    transcriptModel.remove(0)
            }
            function onTranscriptCleared() {
                transcriptModel.clear()
            }
        }

        // ------------------------------------------------------------- footer
        Item {
            id: footer
            height: 48
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            anchors.leftMargin: 26
            anchors.rightMargin: 26

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "ESC  INTERRUPT     CTRL+ALT+V  ACTIVATE     CLICK CORE  TALK"
                color: "#3a556d"
                font.family: "Consolas"
                font.pixelSize: 9
                font.letterSpacing: 2
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 14

                Text {
                    text: "CLEAR"
                    color: clearHover.containsMouse ? "#cfe4f7" : "#3a556d"
                    font.family: "Consolas"
                    font.pixelSize: 9
                    font.letterSpacing: 2
                    MouseArea {
                        id: clearHover
                        anchors.fill: parent
                        anchors.margins: -8
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: victor.clearTranscript()
                    }
                }

                Rectangle {
                    width: 1
                    height: 12
                    color: "#1d3448"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: victor.sessionActive ? "SESSION ACTIVE" : "STANDBY"
                    color: victor.sessionActive ? root.accent : "#3a556d"
                    font.family: "Consolas"
                    font.pixelSize: 9
                    font.letterSpacing: 2
                }
            }
        }
    }
}
