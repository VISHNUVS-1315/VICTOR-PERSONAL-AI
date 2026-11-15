import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: rootWindow
    width: 1360
    height: 860
    minimumWidth: 1080
    minimumHeight: 700
    visible: true
    title: "VICTOR // PERSONAL AI COMMAND CENTER"
    color: "#030712"

    // PROPERTIES & THEME
    property color bgDark: "#030712"
    property color bgPanel: "#071224"
    property color bgCard: "#0b1b33"
    property color bgInput: "#071426"
    property color borderCyan: "#0e3b5e"
    property color borderGlow: "#1e608f"
    property color cyanAccent: "#00f0ff"
    property color cyanMuted: "#38bdf8"
    property color greenAccent: "#00ff9d"
    property color greenMuted: "#34d399"
    property color amberAccent: "#fbbf24"
    property color purpleAccent: "#a855f7"
    property color textWhite: "#f8fafc"
    property color textDim: "#94a3b8"
    property color textMuted: "#475569"

    // ACTIVE VIEW STATE
    // 0: Overview / HUD, 1: AI Chat, 2: Voice Matrix, 3: Memory Bank, 4: Diagnostics & Logs
    property int currentTab: 0

    // SYSTEM STATE FROM BACKEND OR FALLBACK
    // "idle" | "listening" | "thinking" | "speaking" | "sleeping" | "offline"
    property string aiState: (typeof victor !== "undefined" && victor.systemState) ? victor.systemState : "idle"
    property string statusText: (typeof victor !== "undefined" && victor.statusMessage) ? victor.statusMessage : "VICTOR IS STANDING BY"
    property real audioEnergy: (typeof victor !== "undefined") ? victor.audioLevel : 0.0
    property real cpuUsage: (typeof victor !== "undefined") ? victor.cpuUsage : 0.0
    property real ramUsage: (typeof victor !== "undefined") ? victor.ramUsage : 0.0
    property real ramUsedGb: (typeof victor !== "undefined" && victor.ramUsedGb) ? victor.ramUsedGb : 0.0
    property real ramTotalGb: (typeof victor !== "undefined" && victor.ramTotalGb) ? victor.ramTotalGb : 24.0
    property int gpuUsage: (typeof victor !== "undefined") ? victor.gpuUsage : 0
    property int gpuTemp: (typeof victor !== "undefined") ? victor.gpuTemp : 0
    property int gpuVramUsed: (typeof victor !== "undefined" && victor.gpuVramUsed) ? victor.gpuVramUsed : 0
    property bool ollamaOnline: (typeof victor !== "undefined") ? victor.ollamaOnline : true
    property bool wakeWordActive: (typeof victor !== "undefined") ? victor.wakeWordActive : true
    property bool isSleeping: (typeof victor !== "undefined") ? victor.isSleeping : false
    property string powerMode: (typeof victor !== "undefined" && victor.powerMode) ? victor.powerMode : "low_power"
    property string voiceLanguage: (typeof victor !== "undefined" && victor.voiceLanguage) ? victor.voiceLanguage : "auto"
    property string micStatus: (typeof victor !== "undefined" && victor.micStatus) ? victor.micStatus : "STANDBY (WAKE WORD)"

    // SHORTCUTS
    Shortcut {
        sequence: "F11"
        onActivated: rootWindow.visibility = (rootWindow.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen)
    }

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (aiState === "speaking" && typeof victor !== "undefined") {
                victor.stopSpeaking();
            } else if (rootWindow.visibility === Window.FullScreen) {
                rootWindow.visibility = Window.Windowed;
            }
        }
    }

    // ANIMATIONS WITH POWER-MODE AWARE THROTTLING
    property real corePulse: 1.0
    property real ringRotation1: 0.0
    property real ringRotation2: 360.0

    NumberAnimation on corePulse {
        from: 0.94
        to: 1.06
        duration: aiState === "thinking" ? 800 : (aiState === "speaking" ? 600 : (aiState === "sleeping" ? 6000 : (rootWindow.powerMode === "low_power" ? 10000 : (rootWindow.powerMode === "balanced" ? 3000 : 1600))))
        loops: Animation.Infinite
        easing.type: Easing.InOutSine
    }

    NumberAnimation on ringRotation1 {
        from: 0; to: 360
        duration: aiState === "thinking" ? 5000 : (aiState === "sleeping" ? 120000 : (rootWindow.powerMode === "low_power" ? 120000 : (rootWindow.powerMode === "balanced" ? 36000 : 18000)))
        loops: Animation.Infinite
    }

    NumberAnimation on ringRotation2 {
        from: 360; to: 0
        duration: aiState === "thinking" ? 3500 : (aiState === "sleeping" ? 90000 : (rootWindow.powerMode === "low_power" ? 90000 : (rootWindow.powerMode === "balanced" ? 24000 : 12000)))
        loops: Animation.Infinite
    }

    // STATE COLOR HELPER
    function stateColor() {
        if (aiState === "listening") return greenAccent;
        if (aiState === "thinking") return amberAccent;
        if (aiState === "speaking") return purpleAccent;
        if (aiState === "sleeping") return "#475569";
        if (aiState === "offline") return "#ef4444";
        return cyanAccent;
    }

    // INTERNAL CHAT MODEL (backed by python backend signals if present)
    ListModel {
        id: chatHistoryModel

        Component.onCompleted: {
            append({
                "sender": "VICTOR",
                "text": "Greetings, Operator. I am VICTOR, your neural assistant. All local systems, Ollama model inference, and memory banks are standing by. How may I assist you today?",
                "time": "NOW",
                "isUser": false
            });
        }
    }

    // INTERNAL MEMORY MODEL
    ListModel {
        id: memoryModel

        Component.onCompleted: {
            append({"id": 1, "content": "Operator name: Vishnu. Working on AI & Engineering projects."});
            append({"id": 2, "content": "Core LLM configured: Ollama Qwen 3.5 9B."});
            append({"id": 3, "content": "Voice recognition: Faster-Whisper (CPU INT8)."});
        }
    }

    // INTERNAL SYSTEM LOGS MODEL
    ListModel {
        id: systemLogModel

        Component.onCompleted: {
            append({"time": "INIT", "source": "CORE", "msg": "Victor Neural Kernel initialized.", "level": "INFO"});
            append({"time": "BOOT", "source": "LLM", "msg": "Connecting to Ollama endpoint at localhost:11434...", "level": "INFO"});
            append({"time": "BOOT", "source": "MEM", "msg": "SQLite memory storage verified: victor_memory.db", "level": "OK"});
            append({"time": "READY", "source": "AUDIO", "msg": "Audio I/O device ready for voice input.", "level": "OK"});
        }
    }

    // CONNECTIONS TO PYTHON BACKEND
    Connections {
        target: typeof victor !== "undefined" ? victor : null
        ignoreUnknownSignals: true

        function onMessageAdded(role, content, timestamp) {
            chatHistoryModel.append({
                "sender": role.toUpperCase(),
                "text": content,
                "time": timestamp || "NOW",
                "isUser": (role.toLowerCase() === "user")
            });
            chatListView.positionViewAtEnd();
        }

        function onLogAdded(timestamp, source, message, level) {
            systemLogModel.append({
                "time": timestamp,
                "source": source,
                "msg": message,
                "level": level || "INFO"
            });
            if (systemLogModel.count > 150) systemLogModel.remove(0);
        }

        function onMemoriesLoaded(list) {
            memoryModel.clear();
            for (var i = 0; i < list.length; i++) {
                memoryModel.append({
                    "id": list[i].id,
                    "content": list[i].content
                });
            }
        }

        function onSystemStateChanged(state) {
            rootWindow.aiState = state;
        }

        function onStatusMessageChanged(msg) {
            rootWindow.statusText = msg;
        }

        function onAudioLevelChanged(level) {
            rootWindow.audioEnergy = level;
        }

        function onTelemetryUpdated(data) {
            if (data.cpu_percent !== undefined) rootWindow.cpuUsage = data.cpu_percent;
            if (data.ram_percent !== undefined) rootWindow.ramUsage = data.ram_percent;
            if (data.ram_used_gb !== undefined) rootWindow.ramUsedGb = data.ram_used_gb;
            if (data.ram_total_gb !== undefined) rootWindow.ramTotalGb = data.ram_total_gb;
            if (data.gpu && data.gpu.utilization !== undefined) {
                rootWindow.gpuUsage = data.gpu.utilization;
                rootWindow.gpuTemp = data.gpu.temperature;
                if (data.gpu.vram_used_mb !== undefined) rootWindow.gpuVramUsed = data.gpu.vram_used_mb;
            }
            if (data.ollama_online !== undefined) rootWindow.ollamaOnline = data.ollama_online;
            if (data.power_mode !== undefined) rootWindow.powerMode = data.power_mode;
        }

        function onWakeWordToggled(enabled) {
            rootWindow.wakeWordActive = enabled;
        }

        function onPowerModeChanged(mode) {
            rootWindow.powerMode = mode;
        }

        function onVoiceLanguageChanged(lang) {
            rootWindow.voiceLanguage = lang;
        }
    }

    // CLOCK TIMER
    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: {
            var date = new Date();
            var hours = ("0" + date.getHours()).slice(-2);
            var minutes = ("0" + date.getMinutes()).slice(-2);
            var seconds = ("0" + date.getSeconds()).slice(-2);
            timeText.text = hours + ":" + minutes + ":" + seconds;
        }
    }

    // ==========================================
    // PROCEDURAL SCI-FI BACKGROUND
    // ==========================================
    Canvas {
        id: bgCanvas
        anchors.fill: parent
        opacity: 0.45

        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            // Draw Subtle Perspective Cyber Grid
            ctx.strokeStyle = "#081d36";
            ctx.lineWidth = 1;

            var gridSize = 64;
            for (var x = 0; x < width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
            }
            for (var y = 0; y < height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
                ctx.stroke();
            }

            // Radial ambient glow
            var grad = ctx.createRadialGradient(width/2, height/2, 50, width/2, height/2, 550);
            grad.addColorStop(0, "rgba(0, 240, 255, 0.08)");
            grad.addColorStop(0.5, "rgba(5, 40, 75, 0.05)");
            grad.addColorStop(1, "rgba(3, 7, 18, 0)");
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, width, height);
        }
    }

    // ==========================================
    // TOP STATUS / NAVIGATION HEADER
    // ==========================================
    Rectangle {
        id: headerBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 72
        color: bgPanel
        border.color: borderCyan
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            spacing: 20

            // LOGO & IDENTITY
            RowLayout {
                spacing: 14

                Rectangle {
                    width: 44
                    height: 44
                    radius: 8
                    color: "#0a223d"
                    border.color: rootWindow.stateColor()
                    border.width: 2

                    Text {
                        anchors.centerIn: parent
                        text: "V"
                        color: rootWindow.stateColor()
                        font.pixelSize: 26
                        font.bold: true
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "VICTOR"
                        color: textWhite
                        font.pixelSize: 18
                        font.bold: true
                        font.letterSpacing: 4
                    }
                    Text {
                        text: "PERSONAL AI COMMAND INTERFACE"
                        color: cyanMuted
                        font.pixelSize: 9
                        font.bold: true
                        font.letterSpacing: 2
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // NAVIGATION PILLS
            RowLayout {
                spacing: 6

                Repeater {
                    model: [
                        { name: "OVERVIEW", tab: 0, icon: "◈" },
                        { name: "AI CHAT", tab: 1, icon: "💬" },
                        { name: "VOICE SYSTEM", tab: 2, icon: "🎙" },
                        { name: "MEMORY BANK", tab: 3, icon: "🧠" },
                        { name: "TELEMETRY", tab: 4, icon: "⚙" }
                    ]

                    delegate: Rectangle {
                        width: 130
                        height: 38
                        radius: 6
                        color: rootWindow.currentTab === modelData.tab ? "#103254" : "transparent"
                        border.color: rootWindow.currentTab === modelData.tab ? cyanAccent : "transparent"
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            Text {
                                text: modelData.icon
                                color: rootWindow.currentTab === modelData.tab ? cyanAccent : textDim
                                font.pixelSize: 11
                            }
                            Text {
                                text: modelData.name
                                color: rootWindow.currentTab === modelData.tab ? textWhite : textDim
                                font.pixelSize: 11
                                font.bold: rootWindow.currentTab === modelData.tab
                                font.letterSpacing: 1
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            hoverEnabled: true
                            onClicked: rootWindow.currentTab = modelData.tab
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // POWER PROFILE SELECTOR
            RowLayout {
                spacing: 4

                Repeater {
                    model: [
                        { id: "low_power", label: "LOW POWER", icon: "⚡" },
                        { id: "balanced", label: "BALANCED", icon: "⚖" },
                        { id: "performance", label: "PERF", icon: "🚀" }
                    ]

                    delegate: Rectangle {
                        width: 86
                        height: 28
                        radius: 14
                        color: rootWindow.powerMode === modelData.id ? "#0d3b66" : "#051324"
                        border.color: rootWindow.powerMode === modelData.id ? cyanAccent : "#0d2b4a"
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 4
                            Text {
                                text: modelData.icon
                                font.pixelSize: 10
                                color: rootWindow.powerMode === modelData.id ? cyanAccent : textDim
                            }
                            Text {
                                text: modelData.label
                                font.pixelSize: 8
                                font.bold: rootWindow.powerMode === modelData.id
                                font.letterSpacing: 0.5
                                color: rootWindow.powerMode === modelData.id ? textWhite : textDim
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (typeof victor !== "undefined") {
                                    victor.setPowerMode(modelData.id);
                                } else {
                                    rootWindow.powerMode = modelData.id;
                                }
                            }
                        }
                    }
                }
            }

            // SYSTEM TELEMETRY CHIPS & CLOCK
            RowLayout {
                spacing: 16

                Rectangle {
                    height: 28
                    width: 120
                    radius: 14
                    color: "#082138"
                    border.color: rootWindow.stateColor()
                    border.width: 1

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        Rectangle {
                            width: 6; height: 6; radius: 3
                            color: rootWindow.stateColor()
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                NumberAnimation { to: 0.2; duration: 600 }
                                NumberAnimation { to: 1.0; duration: 600 }
                            }
                        }
                        Text {
                            text: rootWindow.aiState.toUpperCase()
                            color: rootWindow.stateColor()
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1
                        }
                    }
                }

                ColumnLayout {
                    spacing: 1
                    Text {
                        id: timeText
                        text: "00:00:00"
                        color: cyanAccent
                        font.pixelSize: 15
                        font.bold: true
                        font.family: "Consolas"
                    }
                    Text {
                        text: "LOCAL NODE"
                        color: textMuted
                        font.pixelSize: 8
                        font.letterSpacing: 1
                    }
                }
            }
        }
    }

    // ==========================================
    // MAIN CONTENT WORKSPACE (STACK OF 5 VIEWS)
    // ==========================================
    Item {
        id: mainWorkspace
        anchors.top: headerBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: bottomDock.top
        anchors.margins: 18

        // -----------------------------------------------------------------
        // VIEW 0: OVERVIEW / HUD
        // -----------------------------------------------------------------
        Item {
            anchors.fill: parent
            visible: rootWindow.currentTab === 0

            // LEFT METRICS COLUMN
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 290
                color: bgPanel
                radius: 10
                border.color: borderCyan
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    Text {
                        text: "SYSTEM SPECIFICATION"
                        color: cyanAccent
                        font.pixelSize: 12
                        font.bold: true
                        font.letterSpacing: 2
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: borderCyan }

                    Repeater {
                        model: [
                            { label: "AI ENGINE", val: "Ollama Local Service" },
                            { label: "ACTIVE LLM", val: "Qwen 3.5 (9B Params)" },
                            { label: "SPEECH INPUT", val: "Faster-Whisper INT8" },
                            { label: "VOICE OUTPUT", val: "Microsoft David (TTS)" },
                            { label: "PERSISTENT MEMORY", val: "SQLite3 Bank" },
                            { label: "HOTWORD LISTENER", val: "OpenWakeWord ('Victor')" }
                        ]

                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3

                            Text {
                                text: modelData.label
                                color: textDim
                                font.pixelSize: 9
                                font.letterSpacing: 1
                            }
                            Text {
                                text: modelData.val
                                color: textWhite
                                font.pixelSize: 12
                                font.bold: true
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // QUICK SYSTEM HEALTH
                    Rectangle {
                        Layout.fillWidth: true
                        height: 90
                        radius: 8
                        color: bgCard
                        border.color: borderGlow
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 6

                            RowLayout {
                                Text { text: "NEURAL ENGINE"; color: rootWindow.ollamaOnline ? greenAccent : amberAccent; font.pixelSize: 10; font.bold: true }
                                Item { Layout.fillWidth: true }
                                Text { text: rootWindow.ollamaOnline ? "ONLINE" : "STANDBY"; color: rootWindow.ollamaOnline ? greenAccent : amberAccent; font.pixelSize: 10; font.bold: true }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 6; radius: 3; color: "#06182c"
                                Rectangle { width: parent.width * (rootWindow.ollamaOnline ? 1.0 : 0.2); height: parent.height; radius: 3; color: rootWindow.ollamaOnline ? greenAccent : amberAccent }
                            }

                            Text {
                                text: rootWindow.ollamaOnline ? "HP Victus 15 // RTX 5060 Ready" : "Run 'ollama serve' if disconnected"
                                color: textDim
                                font.pixelSize: 9
                            }
                        }
                    }
                }
            }

            // CENTER HOLOGRAPHIC ARC REACTOR (VICTOR CORE)
            Item {
                id: centralCoreItem
                anchors.left: parent.left
                anchors.leftMargin: 310
                anchors.right: parent.right
                anchors.rightMargin: 310
                anchors.top: parent.top
                anchors.bottom: parent.bottom

                // ROTATING OUTER GYROSCOPE RING
                Rectangle {
                    id: outerRing
                    width: Math.min(parent.width, parent.height) * 0.72
                    height: width
                    radius: width / 2
                    anchors.centerIn: parent
                    color: "transparent"
                    border.color: "#18456b"
                    border.width: 1
                    rotation: rootWindow.ringRotation1

                    Repeater {
                        model: 24
                        delegate: Rectangle {
                            width: 2; height: 12
                            color: (index % 4 === 0) ? cyanAccent : "#24608f"
                            x: outerRing.width / 2 - width / 2 + (outerRing.width / 2 - 6) * Math.cos(index * Math.PI / 12)
                            y: outerRing.height / 2 - height / 2 + (outerRing.height / 2 - 6) * Math.sin(index * Math.PI / 12)
                            rotation: (index * 15) + 90
                        }
                    }
                }

                // INNER COUNTER-ROTATING RING
                Rectangle {
                    id: innerRing
                    width: outerRing.width * 0.78
                    height: width
                    radius: width / 2
                    anchors.centerIn: parent
                    color: "transparent"
                    border.color: rootWindow.stateColor()
                    border.width: 2
                    opacity: 0.85
                    rotation: rootWindow.ringRotation2

                    Repeater {
                        model: 12
                        delegate: Rectangle {
                            width: 4; height: 16
                            color: rootWindow.stateColor()
                            radius: 2
                            x: innerRing.width / 2 - width / 2 + (innerRing.width / 2 - 8) * Math.cos(index * Math.PI / 6)
                            y: innerRing.height / 2 - height / 2 + (innerRing.height / 2 - 8) * Math.sin(index * Math.PI / 6)
                            rotation: (index * 30) + 90
                        }
                    }
                }

                // PULSING ENERGY SHIELD
                Rectangle {
                    width: innerRing.width * 0.65 * rootWindow.corePulse
                    height: width
                    radius: width / 2
                    anchors.centerIn: parent
                    color: "#07233d"
                    border.color: rootWindow.stateColor()
                    border.width: 2
                    opacity: 0.9

                    // DYNAMIC FREQUENCY RIPPLE BARS
                    Row {
                        anchors.centerIn: parent
                        anchors.verticalCenterOffset: 65
                        spacing: 4

                        Repeater {
                            model: 11
                            delegate: Rectangle {
                                width: 3
                                height: 8 + (Math.sin(index * 0.6 + rootWindow.ringRotation1 * 0.1) + 1) * (rootWindow.aiState === "speaking" ? 18 : 6)
                                color: rootWindow.stateColor()
                                radius: 2
                            }
                        }
                    }
                }

                // CENTER CORE GLYPH
                Column {
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: -12
                    spacing: 2

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "V"
                        color: textWhite
                        font.pixelSize: 84
                        font.bold: true
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "V I C T O R"
                        color: rootWindow.stateColor()
                        font.pixelSize: 13
                        font.bold: true
                        font.letterSpacing: 4
                    }
                }

                // TELEMETRY STATUS UNDER CORE
                Column {
                    anchors.top: outerRing.bottom
                    anchors.topMargin: 12
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 5

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "STATUS // " + rootWindow.statusText.toUpperCase()
                        color: rootWindow.stateColor()
                        font.pixelSize: 12
                        font.bold: true
                        font.letterSpacing: 2
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "CLICK ANYWHERE TO ENGAGE OR USE PROMPT BAR BELOW"
                        color: textDim
                        font.pixelSize: 9
                        font.letterSpacing: 1
                    }
                }
            }

            // RIGHT TELEMETRY & ACTIONS COLUMN
            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 300
                color: bgPanel
                radius: 10
                border.color: borderCyan
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    Text {
                        text: "LIVE TELEMETRY"
                        color: cyanAccent
                        font.pixelSize: 12
                        font.bold: true
                        font.letterSpacing: 2
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: borderCyan }

                    // 1. CPU GAUGE CARD
                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        radius: 8
                        color: bgCard
                        border.color: borderGlow
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            RowLayout {
                                Text { text: "CPU LOAD"; color: textDim; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: rootWindow.cpuUsage.toFixed(1) + "%"
                                    color: rootWindow.cpuUsage > 80 ? "#ef4444" : (rootWindow.cpuUsage > 50 ? amberAccent : cyanAccent)
                                    font.pixelSize: 11
                                    font.bold: true
                                    font.family: "Consolas"
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 5; radius: 2; color: "#05162a"
                                Rectangle {
                                    width: parent.width * Math.min(1.0, Math.max(0.04, rootWindow.cpuUsage / 100.0))
                                    height: parent.height; radius: 2
                                    color: rootWindow.cpuUsage > 80 ? "#ef4444" : (rootWindow.cpuUsage > 50 ? amberAccent : cyanAccent)
                                    Behavior on width { NumberAnimation { duration: 300 } }
                                }
                            }
                            Text { text: "Intel Core i7-13620H (16 Threads)"; color: textMuted; font.pixelSize: 8 }
                        }
                    }

                    // 2. RAM GAUGE CARD
                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        radius: 8
                        color: bgCard
                        border.color: borderGlow
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            RowLayout {
                                Text { text: "RAM USAGE"; color: textDim; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: rootWindow.ramUsedGb > 0 ? (rootWindow.ramUsedGb.toFixed(1) + " / " + rootWindow.ramTotalGb.toFixed(1) + " GB") : (rootWindow.ramUsage.toFixed(1) + "%")
                                    color: rootWindow.ramUsage > 85 ? "#ef4444" : (rootWindow.ramUsage > 70 ? amberAccent : greenAccent)
                                    font.pixelSize: 11
                                    font.bold: true
                                    font.family: "Consolas"
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 5; radius: 2; color: "#05162a"
                                Rectangle {
                                    width: parent.width * Math.min(1.0, Math.max(0.05, rootWindow.ramUsage / 100.0))
                                    height: parent.height; radius: 2
                                    color: rootWindow.ramUsage > 85 ? "#ef4444" : (rootWindow.ramUsage > 70 ? amberAccent : greenAccent)
                                    Behavior on width { NumberAnimation { duration: 300 } }
                                }
                            }
                            Text { text: "24 GB DDR5 (" + rootWindow.ramUsage.toFixed(0) + "% allocated)"; color: textMuted; font.pixelSize: 8 }
                        }
                    }

                    // 3. GPU GAUGE CARD (RTX 5060)
                    Rectangle {
                        Layout.fillWidth: true
                        height: 60
                        radius: 8
                        color: bgCard
                        border.color: borderGlow
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 4

                            RowLayout {
                                Text { text: "RTX 5060 GPU"; color: textDim; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: (rootWindow.gpuTemp > 0 ? (rootWindow.gpuTemp + "°C | ") : "") + rootWindow.gpuUsage + "%" + (rootWindow.gpuVramUsed > 0 ? (" | " + (rootWindow.gpuVramUsed/1024).toFixed(1) + "GB") : "")
                                    color: purpleAccent
                                    font.pixelSize: 11
                                    font.bold: true
                                    font.family: "Consolas"
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true; height: 5; radius: 2; color: "#05162a"
                                Rectangle {
                                    width: parent.width * Math.min(1.0, Math.max(0.05, rootWindow.gpuUsage / 100.0))
                                    height: parent.height; radius: 2
                                    color: purpleAccent
                                    Behavior on width { NumberAnimation { duration: 300 } }
                                }
                            }
                            Text { text: "8GB VRAM // Dedicated Silicon"; color: textMuted; font.pixelSize: 8 }
                        }
                    }

                    // 4. SUBSYSTEM STATUS PILLS
                    Rectangle {
                        Layout.fillWidth: true
                        height: 104
                        radius: 8
                        color: "#061324"
                        border.color: borderCyan
                        border.width: 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 5

                            // Ollama Status Row
                            RowLayout {
                                Text { text: "OLLAMA ENGINE:"; color: textDim; font.pixelSize: 9 }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: rootWindow.ollamaOnline ? greenAccent : "#ef4444"
                                }
                                Text {
                                    text: rootWindow.ollamaOnline ? "ONLINE (QWEN 9B)" : "STANDBY"
                                    color: rootWindow.ollamaOnline ? greenAccent : "#ef4444"
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }

                            // Wake-word row & toggle button
                            RowLayout {
                                Text { text: "WAKE WORD ('VICTOR'):"; color: textDim; font.pixelSize: 9 }
                                Item { Layout.fillWidth: true }
                                Rectangle {
                                    height: 18
                                    width: 58
                                    radius: 9
                                    color: rootWindow.wakeWordActive ? "#064e3b" : "#374151"
                                    border.color: rootWindow.wakeWordActive ? greenAccent : textMuted
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: rootWindow.wakeWordActive ? "ACTIVE" : "PAUSED"
                                        color: rootWindow.wakeWordActive ? greenAccent : textDim
                                        font.pixelSize: 8
                                        font.bold: true
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof victor !== "undefined") victor.toggleWakeWord();
                                        }
                                    }
                                }
                            }

                            // Microphone Status Row
                            RowLayout {
                                Text { text: "MICROPHONE:"; color: textDim; font.pixelSize: 9 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: rootWindow.micStatus
                                    color: rootWindow.aiState === "listening" ? greenAccent : cyanMuted
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }

                            // Power Profile Row
                            RowLayout {
                                Text { text: "POWER PROFILE:"; color: textDim; font.pixelSize: 9 }
                                Item { Layout.fillWidth: true }
                                Text {
                                    text: rootWindow.powerMode.toUpperCase()
                                    color: rootWindow.powerMode === "low_power" ? greenAccent : (rootWindow.powerMode === "balanced" ? cyanAccent : amberAccent)
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // 5. QUICK ACTIONS PANEL
                    Text {
                        text: "SYSTEM SHORTCUTS"
                        color: cyanMuted
                        font.pixelSize: 10
                        font.bold: true
                        font.letterSpacing: 1
                    }

                    GridLayout {
                        columns: 2
                        columnSpacing: 8
                        rowSpacing: 8
                        Layout.fillWidth: true

                        // Screenshot Button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 38
                            radius: 6
                            color: bgCard
                            border.color: borderCyan
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "📸"; font.pixelSize: 12 }
                                Text { text: "SCREENSHOT"; color: textWhite; font.pixelSize: 9; font.bold: true }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onEntered: parent.border.color = cyanAccent
                                onExited: parent.border.color = borderCyan
                                onClicked: {
                                    if (typeof victor !== "undefined") victor.executeAction("screenshot", "");
                                }
                            }
                        }

                        // VS Code Button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 38
                            radius: 6
                            color: bgCard
                            border.color: borderCyan
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "💻"; font.pixelSize: 12 }
                                Text { text: "VS CODE"; color: textWhite; font.pixelSize: 9; font.bold: true }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onEntered: parent.border.color = cyanAccent
                                onExited: parent.border.color = borderCyan
                                onClicked: {
                                    if (typeof victor !== "undefined") victor.executeAction("open_app", "code");
                                }
                            }
                        }

                        // Sleep Button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 38
                            radius: 6
                            color: bgCard
                            border.color: borderCyan
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "🌙"; font.pixelSize: 12 }
                                Text { text: "STANDBY"; color: textWhite; font.pixelSize: 9; font.bold: true }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onEntered: parent.border.color = amberAccent
                                onExited: parent.border.color = borderCyan
                                onClicked: {
                                    if (typeof victor !== "undefined") victor.toggleSleep();
                                }
                            }
                        }

                        // Fullscreen Button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 38
                            radius: 6
                            color: bgCard
                            border.color: borderCyan
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                Text { text: "⛶"; font.pixelSize: 12 }
                                Text { text: "FULLSCREEN"; color: textWhite; font.pixelSize: 9; font.bold: true }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                hoverEnabled: true
                                onEntered: parent.border.color = cyanAccent
                                onExited: parent.border.color = borderCyan
                                onClicked: {
                                    rootWindow.visibility = (rootWindow.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen);
                                }
                            }
                        }
                    }
                }
            }
        }

        // -----------------------------------------------------------------
        // VIEW 1: AI CHAT CONSOLE
        // -----------------------------------------------------------------
        Item {
            anchors.fill: parent
            visible: rootWindow.currentTab === 1

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                // CHAT MESSAGE LIST
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: bgPanel
                    radius: 10
                    border.color: borderCyan
                    border.width: 1
                    clip: true

                    ListView {
                        id: chatListView
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14
                        model: chatHistoryModel

                        delegate: RowLayout {
                            width: chatListView.width - 24
                            layoutDirection: model.isUser ? Qt.RightToLeft : Qt.LeftToRight
                            spacing: 12

                            // AVATAR
                            Rectangle {
                                width: 34; height: 34; radius: 17
                                color: model.isUser ? "#0e4a77" : "#0d3a33"
                                border.color: model.isUser ? cyanAccent : greenAccent
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: model.isUser ? "YOU" : "V"
                                    color: model.isUser ? cyanAccent : greenAccent
                                    font.pixelSize: 10
                                    font.bold: true
                                }
                            }

                            // MESSAGE BUBBLE
                            Rectangle {
                                Layout.maximumWidth: parent.width * 0.75
                                width: Math.min(msgText.implicitWidth + 28, parent.width * 0.75)
                                height: msgText.implicitHeight + 28
                                radius: 10
                                color: model.isUser ? "#0a2642" : bgCard
                                border.color: model.isUser ? "#195788" : borderCyan
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4

                                    RowLayout {
                                        Text {
                                            text: model.sender
                                            color: model.isUser ? cyanAccent : greenAccent
                                            font.pixelSize: 10
                                            font.bold: true
                                            font.letterSpacing: 1
                                        }
                                        Item { Layout.fillWidth: true }
                                        Text {
                                            text: model.time
                                            color: textMuted
                                            font.pixelSize: 9
                                        }
                                    }

                                    Text {
                                        id: msgText
                                        text: model.text
                                        color: textWhite
                                        font.pixelSize: 13
                                        wrapMode: Text.Wrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }
                }

                // SUGGESTED QUICK PROMPTS
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: [
                            "What are your core capabilities?",
                            "Show me saved memories",
                            "Explain quantum computing in simple terms",
                            "Clear conversation"
                        ]

                        delegate: Rectangle {
                            height: 28
                            width: chipText.implicitWidth + 24
                            radius: 14
                            color: bgCard
                            border.color: borderCyan
                            border.width: 1

                            Text {
                                id: chipText
                                anchors.centerIn: parent
                                text: modelData
                                color: cyanMuted
                                font.pixelSize: 10
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (modelData === "Clear conversation") {
                                        chatHistoryModel.clear();
                                    } else {
                                        promptInput.text = modelData;
                                        sendChatAction();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // -----------------------------------------------------------------
        // VIEW 2: VOICE SYSTEM STUDIO
        // -----------------------------------------------------------------
        Item {
            anchors.fill: parent
            visible: rootWindow.currentTab === 2

            RowLayout {
                anchors.fill: parent
                spacing: 20

                // VOICE INTERACTION SPHERE
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: bgPanel
                    radius: 10
                    border.color: borderCyan
                    border.width: 1

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 28

                        // LARGE PULSING MIC BUTTON
                        Rectangle {
                            id: bigMicBtn
                            width: 180
                            height: 180
                            radius: 90
                            anchors.horizontalCenter: parent.horizontalCenter
                            color: rootWindow.aiState === "listening" ? "#064e3b" : "#082a47"
                            border.color: rootWindow.aiState === "listening" ? greenAccent : cyanAccent
                            border.width: 3

                            SequentialAnimation on scale {
                                running: rootWindow.aiState === "listening"
                                loops: Animation.Infinite
                                NumberAnimation { to: 1.08; duration: 600; easing.type: Easing.InOutQuad }
                                NumberAnimation { to: 1.0; duration: 600; easing.type: Easing.InOutQuad }
                            }

                            Column {
                                anchors.centerIn: parent
                                spacing: 8

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "🎙"
                                    font.pixelSize: 48
                                    color: rootWindow.aiState === "listening" ? greenAccent : cyanAccent
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: rootWindow.aiState === "listening" ? "LISTENING..." : "PUSH TO TALK"
                                    color: textWhite
                                    font.pixelSize: 11
                                    font.bold: true
                                    font.letterSpacing: 1
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof victor !== "undefined") {
                                        victor.startVoiceInput();
                                    } else {
                                        rootWindow.aiState = (rootWindow.aiState === "listening") ? "idle" : "listening";
                                    }
                                }
                            }
                        }

                        // AUDIO WAVEFORM PREVIEW
                        Row {
                            anchors.horizontalCenter: parent.horizontalCenter
                            spacing: 6

                            Repeater {
                                model: 16
                                delegate: Rectangle {
                                    width: 5
                                    height: 12 + Math.random() * (rootWindow.aiState === "listening" ? 45 : 10)
                                    color: rootWindow.aiState === "listening" ? greenAccent : cyanMuted
                                    radius: 3
                                }
                            }
                        }

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "SPEECH RECOGNITION: FASTER-WHISPER | WAKE WORD: 'VICTOR' (CUSTOM ONNX)"
                            color: textDim
                            font.pixelSize: 10
                            font.letterSpacing: 1
                        }
                    }
                }

                // VOICE CONTROLS & SETTINGS
                Rectangle {
                    width: 340
                    Layout.fillHeight: true
                    color: bgPanel
                    radius: 10
                    border.color: borderCyan
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 16

                        Text {
                            text: "VOICE ENGINE PARAMETERS"
                            color: cyanAccent
                            font.pixelSize: 12
                            font.bold: true
                            font.letterSpacing: 2
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: borderCyan }

                        Text { text: "Active TTS Voice: Microsoft David Desktop"; color: textWhite; font.pixelSize: 11 }
                        Text { text: "Sampling Rate: 16,000 Hz (Float32)"; color: textDim; font.pixelSize: 10 }
                        Text { text: "Adaptive VAD Silence Endpoint: 800–1200 ms"; color: textDim; font.pixelSize: 10 }
                        Text { text: "Dynamic Noise Floor Calibration: ACTIVE"; color: textDim; font.pixelSize: 10 }
                        Text { text: "Sentence Max Duration: 30.0 Seconds"; color: textDim; font.pixelSize: 10 }

                        Rectangle { Layout.fillWidth: true; height: 1; color: borderCyan }

                        Text {
                            text: "LANGUAGE MODE"
                            color: cyanAccent
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1
                        }

                        RowLayout {
                            spacing: 6
                            Repeater {
                                model: [
                                    { id: "auto", label: "AUTO (EN/TA)" },
                                    { id: "en", label: "ENGLISH" },
                                    { id: "ta", label: "தமிழ்" }
                                ]
                                delegate: Rectangle {
                                    width: 88
                                    height: 28
                                    radius: 6
                                    color: rootWindow.voiceLanguage === modelData.id ? "#103254" : bgCard
                                    border.color: rootWindow.voiceLanguage === modelData.id ? cyanAccent : borderCyan
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        color: rootWindow.voiceLanguage === modelData.id ? textWhite : textDim
                                        font.pixelSize: 9
                                        font.bold: rootWindow.voiceLanguage === modelData.id
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof victor !== "undefined") victor.setVoiceLanguage(modelData.id);
                                            else rootWindow.voiceLanguage = modelData.id;
                                        }
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }

                        // TEST TTS BUTTON
                        Rectangle {
                            Layout.fillWidth: true
                            height: 44
                            radius: 8
                            color: "#0c3150"
                            border.color: cyanAccent
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "🔊 TEST VICTOR VOICE"
                                color: textWhite
                                font.pixelSize: 11
                                font.bold: true
                                font.letterSpacing: 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (typeof victor !== "undefined") {
                                        victor.speak("Voice output operational. Victor speech synthesis is online.");
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // -----------------------------------------------------------------
        // VIEW 3: MEMORY MATRIX (SQLITE STORE)
        // -----------------------------------------------------------------
        Item {
            anchors.fill: parent
            visible: rootWindow.currentTab === 3

            ColumnLayout {
                anchors.fill: parent
                spacing: 14

                // MEMORY HEADER & ADD INPUT
                Rectangle {
                    Layout.fillWidth: true
                    height: 70
                    color: bgPanel
                    radius: 10
                    border.color: borderCyan
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 12

                        TextField {
                            id: newMemoryField
                            Layout.fillWidth: true
                            height: 42
                            placeholderText: "Type a personal fact or rule for Victor to remember permanently..."
                            placeholderTextColor: textMuted
                            color: textWhite
                            font.pixelSize: 12
                            background: Rectangle {
                                color: bgInput
                                radius: 6
                                border.color: newMemoryField.activeFocus ? cyanAccent : borderCyan
                                border.width: 1
                            }
                            onAccepted: commitMemoryAction()
                        }

                        Rectangle {
                            width: 150
                            height: 40
                            radius: 6
                            color: "#083329"
                            border.color: greenAccent
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "+ COMMIT MEMORY"
                                color: greenAccent
                                font.pixelSize: 10
                                font.bold: true
                                font.letterSpacing: 1
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: commitMemoryAction()
                            }
                        }
                    }
                }

                // MEMORY LIST
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: bgPanel
                    radius: 10
                    border.color: borderCyan
                    border.width: 1

                    ListView {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10
                        model: memoryModel
                        clip: true

                        delegate: Rectangle {
                            width: parent.width - 12
                            height: 60
                            radius: 8
                            color: bgCard
                            border.color: borderCyan
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 16
                                anchors.rightMargin: 16
                                spacing: 14

                                Rectangle {
                                    width: 28; height: 28; radius: 14
                                    color: "#0c2c47"
                                    border.color: cyanMuted
                                    border.width: 1
                                    Text {
                                        anchors.centerIn: parent
                                        text: "#" + model.id
                                        color: cyanMuted
                                        font.pixelSize: 10
                                        font.bold: true
                                    }
                                }

                                Text {
                                    text: model.content
                                    color: textWhite
                                    font.pixelSize: 12
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    width: 32; height: 32; radius: 6
                                    color: "#2a1017"
                                    border.color: "#ef4444"
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: "✕"
                                        color: "#ef4444"
                                        font.pixelSize: 12
                                        font.bold: true
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (typeof victor !== "undefined") {
                                                victor.deleteMemory(model.id);
                                            }
                                            memoryModel.remove(index);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // -----------------------------------------------------------------
        // VIEW 4: TELEMETRY & LOGS
        // -----------------------------------------------------------------
        Item {
            anchors.fill: parent
            visible: rootWindow.currentTab === 4

            RowLayout {
                anchors.fill: parent
                spacing: 18

                // HARDWARE & SUBSYSTEM GAUGES
                Rectangle {
                    width: 340
                    Layout.fillHeight: true
                    color: bgPanel
                    radius: 10
                    border.color: borderCyan
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 16

                        Text {
                            text: "SUBSYSTEM TELEMETRY"
                            color: cyanAccent
                            font.pixelSize: 12
                            font.bold: true
                            font.letterSpacing: 2
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: borderCyan }

                        Repeater {
                            model: [
                                { name: "Ollama LLM Engine", status: "ONLINE", port: "11434", ping: "12ms", ok: true },
                                { name: "Faster-Whisper STT", status: "READY", port: "Local CPU", ping: "INT8 (VAD)", ok: true },
                                { name: "PyTTSx3 Speech Synth", status: "ACTIVE", port: "SAPI5", ping: "Ready", ok: true },
                                { name: "SQLite Memory DB", status: "MOUNTED", port: "victor_memory.db", ping: "Synced", ok: true },
                                { name: "Wake-Word Listener", status: "STANDBY", port: "OpenWakeWord", ping: "Victor (ONNX)", ok: true }
                            ]

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                height: 56
                                radius: 6
                                color: bgCard
                                border.color: borderGlow
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12

                                    ColumnLayout {
                                        spacing: 2
                                        Text { text: modelData.name; color: textWhite; font.pixelSize: 11; font.bold: true }
                                        Text { text: modelData.port; color: textDim; font.pixelSize: 9 }
                                    }

                                    Item { Layout.fillWidth: true }

                                    ColumnLayout {
                                        spacing: 2
                                        Text { text: modelData.status; color: modelData.ok ? greenAccent : amberAccent; font.pixelSize: 10; font.bold: true }
                                        Text { text: modelData.ping; color: textDim; font.pixelSize: 9 }
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }

                // LIVE TERMINAL LOGS
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#020713"
                    radius: 10
                    border.color: borderCyan
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "REAL-TIME DIAGNOSTIC EVENT STREAM"
                                color: greenAccent
                                font.pixelSize: 11
                                font.bold: true
                                font.letterSpacing: 1
                                font.family: "Consolas"
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                text: "CLEAR"
                                color: textDim
                                font.pixelSize: 10
                                font.bold: true
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: systemLogModel.clear()
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: "#0d2b45" }

                        ListView {
                            id: logListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: systemLogModel
                            clip: true
                            spacing: 6

                            delegate: RowLayout {
                                width: logListView.width
                                spacing: 12

                                Text {
                                    text: "[" + model.time + "]"
                                    color: textMuted
                                    font.pixelSize: 10
                                    font.family: "Consolas"
                                }

                                Text {
                                    text: "[" + model.source + "]"
                                    color: cyanAccent
                                    font.pixelSize: 10
                                    font.bold: true
                                    font.family: "Consolas"
                                }

                                Text {
                                    text: model.msg
                                    color: model.level === "OK" ? greenAccent : (model.level === "WARN" ? amberAccent : textWhite)
                                    font.pixelSize: 10
                                    font.family: "Consolas"
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ==========================================
    // BOTTOM COMMAND BAR & DOCK
    // ==========================================
    Rectangle {
        id: bottomDock
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 80
        color: bgPanel
        border.color: borderCyan
        border.width: 1

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 12

            // MIC PUSH-TO-TALK BUTTON
            Rectangle {
                width: 48
                height: 48
                radius: 24
                color: rootWindow.aiState === "listening" ? "#064e3b" : "#0d3152"
                border.color: rootWindow.aiState === "listening" ? greenAccent : cyanAccent
                border.width: 2

                Text {
                    anchors.centerIn: parent
                    text: "🎙"
                    font.pixelSize: 18
                    color: rootWindow.aiState === "listening" ? greenAccent : cyanAccent
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof victor !== "undefined") {
                            victor.startVoiceInput();
                        } else {
                            rootWindow.aiState = (rootWindow.aiState === "listening") ? "idle" : "listening";
                        }
                    }
                }
            }

            // DYNAMIC AUDIO EQUALIZER (Reacts to user voice & Victor speech)
            Row {
                spacing: 3
                Layout.alignment: Qt.AlignVCenter

                Repeater {
                    model: 8
                    delegate: Rectangle {
                        width: 4
                        height: 6 + Math.max(0, (rootWindow.audioEnergy * 32.0 * (0.5 + 0.5 * Math.sin(index * 0.9))))
                        radius: 2
                        color: rootWindow.stateColor()
                        opacity: rootWindow.audioEnergy > 0.05 ? 0.95 : 0.3
                        Behavior on height { NumberAnimation { duration: 60 } }
                    }
                }
            }

            // COMMAND TEXT INPUT
            TextField {
                id: promptInput
                Layout.fillWidth: true
                height: 48
                placeholderText: "Transcribe voice or type command for Victor... (Press Enter to execute)"
                placeholderTextColor: textMuted
                color: textWhite
                font.pixelSize: 13
                background: Rectangle {
                    color: bgInput
                    radius: 8
                    border.color: promptInput.activeFocus ? cyanAccent : borderCyan
                    border.width: 1
                }
                onAccepted: sendChatAction()
            }

            // TRANSMIT / SEND BUTTON
            Rectangle {
                width: 100
                height: 46
                radius: 8
                color: "#0a3a60"
                border.color: cyanAccent
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    Text {
                        text: "SEND"
                        color: textWhite
                        font.pixelSize: 11
                        font.bold: true
                        font.letterSpacing: 2
                    }
                    Text {
                        text: "➤"
                        color: cyanAccent
                        font.pixelSize: 12
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onEntered: parent.color = "#0e4d80"
                    onExited: parent.color = "#0a3a60"
                    onClicked: sendChatAction()
                }
            }

            // STOP SPEAKING BUTTON (Visible when Victor is speaking)
            Rectangle {
                visible: rootWindow.aiState === "speaking"
                width: 90
                height: 46
                radius: 8
                color: "#450a0a"
                border.color: "#ef4444"
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 4
                    Text { text: "⏹"; color: "#ef4444"; font.pixelSize: 12 }
                    Text { text: "STOP"; color: textWhite; font.pixelSize: 10; font.bold: true }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (typeof victor !== "undefined") victor.stopSpeaking();
                    }
                }
            }

            // SLEEP / STANDBY TOGGLE BUTTON
            Rectangle {
                width: 44
                height: 44
                radius: 8
                color: rootWindow.aiState === "sleeping" ? "#1e293b" : bgCard
                border.color: rootWindow.aiState === "sleeping" ? amberAccent : borderCyan
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: rootWindow.aiState === "sleeping" ? "☀" : "🌙"
                    font.pixelSize: 16
                    color: rootWindow.aiState === "sleeping" ? amberAccent : textDim
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onEntered: parent.border.color = amberAccent
                    onExited: parent.border.color = rootWindow.aiState === "sleeping" ? amberAccent : borderCyan
                    onClicked: {
                        if (typeof victor !== "undefined") victor.toggleSleep();
                    }
                }
            }

            // FULLSCREEN TOGGLE BUTTON
            Rectangle {
                width: 44
                height: 44
                radius: 8
                color: bgCard
                border.color: borderCyan
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "⛶"
                    font.pixelSize: 16
                    color: textDim
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onEntered: parent.border.color = cyanAccent
                    onExited: parent.border.color = borderCyan
                    onClicked: {
                        rootWindow.visibility = (rootWindow.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen);
                    }
                }
            }
        }
    }

    // HELPER ACTIONS
    function sendChatAction() {
        var query = promptInput.text.trim();
        if (!query) return;

        // Add to chat list
        var date = new Date();
        var timeStr = ("0" + date.getHours()).slice(-2) + ":" + ("0" + date.getMinutes()).slice(-2);

        chatHistoryModel.append({
            "sender": "YOU",
            "text": query,
            "time": timeStr,
            "isUser": true
        });

        promptInput.text = "";

        // Switch to chat view if on HUD overview
        if (rootWindow.currentTab === 0) {
            rootWindow.currentTab = 1;
        }

        // Forward to Python backend
        if (typeof victor !== "undefined") {
            victor.sendMessage(query);
        } else {
            // Standalone simulated reply
            rootWindow.aiState = "thinking";
            simulateAiReply(query);
        }
    }

    function simulateAiReply(userText) {
        simTimer.query = userText;
        simTimer.start();
    }

    Timer {
        id: simTimer
        interval: 900
        property string query: ""
        onTriggered: {
            rootWindow.aiState = "speaking";
            var date = new Date();
            var timeStr = ("0" + date.getHours()).slice(-2) + ":" + ("0" + date.getMinutes()).slice(-2);
            var reply = "Victor acknowledged: '" + query + "'. I am standing by with full neural processing capabilities.";

            chatHistoryModel.append({
                "sender": "VICTOR",
                "text": reply,
                "time": timeStr,
                "isUser": false
            });

            chatListView.positionViewAtEnd();
            resetStateTimer.start();
        }
    }

    Timer {
        id: resetStateTimer
        interval: 1800
        onTriggered: rootWindow.aiState = "idle"
    }

    function commitMemoryAction() {
        var mem = newMemoryField.text.trim();
        if (!mem) return;

        if (typeof victor !== "undefined") {
            victor.addMemory(mem);
        }

        memoryModel.append({
            "id": memoryModel.count + 1,
            "content": mem
        });

        newMemoryField.text = "";
    }
}
