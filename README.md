
# VICTOR // Advanced Personal AI Command Center

> **Futuristic, Iron Man JARVIS-inspired personal AI assistant engineered natively for Windows 11.**

[![Python 3.14.2](https://img.shields.io/badge/Python-3.14.2-blue.svg)](https://www.python.org/)
[![Local AI](https://img.shields.io/badge/Ollama-Qwen_3.5_9B-cyan.svg)](https://ollama.com/)
[![Speech](https://img.shields.io/badge/Faster--Whisper-INT8-green.svg)](https://github.com/SYSTRAN/faster-whisper)
[![Wake Word](https://img.shields.io/badge/Wake_Word-Victor-orange.svg)](https://github.com/dscripka/openWakeWord)
[![GPU Accelerated](https://img.shields.io/badge/NVIDIA-RTX_5060_8GB-76B900.svg)](https://www.nvidia.com/)

---

## 1. System Overview

VICTOR is a local-first, privacy-respecting, hands-free personal AI assistant designed specifically for an **HP Victus 15** laptop (Intel Core i7-13620H, 24GB DDR5, NVIDIA GeForce RTX 5060).

VICTOR features a cinematic holographic interface powered by **PySide6 & QML**, driven by an offline background listener for the exact wake word **"Victor"**, backed by **Faster-Whisper** automatic speech recognition, **Microsoft David / Zira** natural TTS speech synthesis, persistent **SQLite long-term memory**, and local neural inference via **Ollama (Qwen 3.5 9B)**.

```
                      +-----------------------------+
                      |   OPERATOR (Speech / Text)  |
                      +--------------+--------------+
                                     |
                                     v
                  +-------------------------------------+
                  |   CUSTOM WAKE WORD: "VICTOR"        |
                  |   openWakeWord (victor.onnx)        |
                  +------------------+------------------+
                                     | (Activation Chime)
                                     v
                  +-------------------------------------+
                  |   FASTER-WHISPER SPEECH-TO-TEXT     |
                  |   CPU INT8 Quantized / VAD Engine   |
                  +------------------+------------------+
                                     | (Transcript)
                                     v
                  +-------------------------------------+
                  |   VICTOR COGNITIVE BRAIN            |
                  |   Ollama Qwen 3.5 (9B Params)       |
                  |   - English / Tamil Context         |
                  |   - SQLite Memory Context Injection |
                  +--------+-------------------+--------+
                           |                   |
          (Action Tag)     |                   | (Speech Text)
                           v                   v
+-----------------------------+    +-----------------------------+
| COMPUTER AUTOMATION SYSTEM  |    | NATURAL VOICE SYNTHESIS     |
| - App Launcher (Whitelist)  |    | - PyTTSx3 (David / Zira)    |
| - Volume & Media Keybd Ctrl |    | - Speech Interruption (Stop)|
| - Screenshots (Pillow)      |    | - Waveform Level Streaming  |
| - RTX 5060 & CPU Diagnostics|    +--------------+--------------+
+-----------------------------+                   |
                           ^                      |
                           |                      v
                  +--------+----------------------+-----+
                  |   HOLOGRAPHIC JARVIS UI (PySide6)   |
                  |   - Animated AI Arc Reactor / Core  |
                  |   - Rotating Concentric Energy Rings|
                  |   - Audio-Reactive Equalizer Waveform|
                  |   - Real-Time Hardware Telemetry    |
                  +-------------------------------------+
```

---

## 2. Key Features

### 🌟 Advanced JARVIS Holographic UI
- **Futuristic Palette**: Deep obsidian (#030712) and navy glass panels accented with electric cyan (#00f0ff), mint green (#00ff9d), amber, and purple.
- **Central Arc Reactor**: Concentric rotating rings with energy pulsation and dynamic frequency ripple bars.
- **Three Power Profiles**:
  - `Low Power` (Default): Lowest CPU, GPU, and RAM footprint. Ring rotation slowed to 120s, background telemetry interval throttled to 3.5s, idle animations paused/slowed.
  - `Balanced`: Moderate visual effects, 2.0s telemetry interval, smooth 30s gyroscopic ring rotations.
  - `Performance`: Full speed animations (18s / 12s), dynamic audio ripple bars, and 1.0s real-time telemetry.
  - Switch via UI header pills or voice commands: *"Low power mode"*, *"Balanced mode"*, *"Performance mode"*.
- **Live System States**: 
  - `IDLE`: Ambient breathing blue core.
  - `LISTENING`: Electric green mic glow with real-time audio waveform.
  - `THINKING`: High-speed amber reactor spin during Ollama inference.
  - `SPEAKING`: Voice-reactive visualizer dancing to Victor's audio output.
  - `SLEEPING`: Dimmed low-power standby mode with minimized CPU footprint.
  - `OFFLINE`: Visual diagnostic status indicator.
- **Real-Time Telemetry Gauges**: Real CPU load %, 24GB DDR5 RAM allocation in GB (`used / total GB`), NVIDIA GeForce RTX 5060 GPU temperature, utilization & VRAM in MB, Ollama status, Wake-word status, and Mic status.

### 🎙 Reliable Voice Recognition & Custom Wake Word ("Victor")
- **Custom Offline Wake Word**: Native, lightweight detection trained specifically for the keyword **"Victor"** (`data/models/victor.onnx`) with single-thread pool constraint (`OMP_NUM_THREADS=1`) to eliminate excessive CPU core wakeups.
- **Dynamic Noise Floor Calibration**: Samples the first 300ms of ambient room sound upon activation to calibrate the speech threshold dynamically.
- **1.0-Second Pre-Speech Ring Buffer**: Maintains a circular rolling buffer of recent audio chunks so beginning consonants and quiet syllables are never clipped.
- **Adaptive Silence Endpointing (800–1200 ms)**: Waits patiently for 1.0 second of natural silence before finalizing speech, allowing complex, multi-clause sentences (up to 30s) without cutting the speaker off prematurely.
- **Short Noise Spike Filter**: Automatically discards transient clicks, keyboard clatter, or breathing (<0.5s).
- **Self-Speech Suppression & Concurrency Lock**: Wake-word detector is automatically paused during speech capture, Ollama inference, and TTS playback, eliminating audio feedback and ensuring **exactly one response per command**.
- **Speech Interruption**: Operator can interrupt Victor instantly via the UI **STOP** button, `Escape` key, or voice commands: *"Stop talking"*, *"Be quiet"*.
- **Multi-Language Support**: Seamlessly handles English, Tamil, and Tanglish with manual language override or auto-detection.

### 🧠 Intelligent Cognitive Brain (Qwen 3.5 9B)
- Local inference through Ollama with zero reliance on paid cloud APIs.
- Conversational understanding of natural English and Tamil/Tanglish.
- Conversational context window maintaining memory of recent conversation turns.
- Calibrated personality: Intelligent, calm, confident, professional, and precise.

### 💾 Persistent Long-Term Memory
- SQLite database (`data/victor_memory.db`) storing user preferences, ongoing projects, and facts.
- Category tagging (`project`, `preference`, `skill`, `general`).
- Automatic security filtering: Blocks passwords, API keys, private keys, and credit cards from memory.
- Conversational memory inspection and deletion directly in the UI.

### ⚙ Secure Computer Control & Automation
- Whitelist-enforced application launcher (`code`, `cursor`, `chrome`, `brave`, `calc`, `notepad`, `wt`, `taskmgr`, `spotify`, etc.).
- Audio volume control via `pycaw` (set percentage, mute, unmute, volume up/down).
- Media playback control via virtual keystrokes (play/pause, next track, previous track).
- Screen capture utility saving timestamps to `data/screenshots/`.
- Hardware telemetry (CPU cores, RAM usage, RTX 5060 GPU temperature & VRAM).
- Audit activity logging stored in SQLite.

---

## 3. Directory Layout

```
C:\VICTOR
├── assets/
│   ├── sounds/               # Procedural audio effects (activation, acknowledge, sleep)
│   └── icons/                # Interface icons
├── config/
│   └── settings.json         # User settings & configuration
├── data/
│   ├── models/
│   │   └── victor.onnx       # Custom trained wake-word ONNX model
│   ├── screenshots/          # Screen captures saved by Victor
│   └── victor_memory.db      # SQLite persistent memory & audit store
├── scripts/
│   └── train_victor_model.py # Automated synthetic training pipeline for 'Victor'
├── src/
│   ├── actions/
│   │   └── computer_control.py # Whitelist automation, pycaw volume, screenshots
│   ├── brain/
│   │   └── llm.py            # Ollama Qwen 3.5 9B conversation engine
│   ├── config/
│   │   └── settings.py       # Configuration manager singleton
│   ├── core/
│   │   ├── audio_effects.py  # Sci-Fi sound effect synthesizer
│   │   └── state.py          # Central state machine (IDLE, LISTENING, etc.)
│   ├── memory/
│   │   └── store.py          # SQLite database wrapper with migration & security
│   ├── services/
│   │   └── telemetry_service.py # Background hardware poller (CPU, RAM, GPU)
│   ├── ui/
│   │   ├── qml/
│   │   │   └── Main.qml      # Full-Screen JARVIS Holographic HUD
│   │   ├── web/
│   │   │   └── index.html    # Standalone browser UI fallback
│   │   └── main.py           # PySide6 master application backend
│   └── voice/
│       ├── stt.py            # Faster-Whisper INT8 speech-to-text
│       ├── tts.py            # Natural PyTTSx3 speech synthesis with interrupt
│       └── wake_word.py      # Background listener for 'Victor'
├── tests/
│   └── test_victor.py        # Automated test suite for all 9 subsystems
├── requirements.txt
├── run_ui.bat                # Windows interactive command center launcher
├── run_victor.py             # Master python launcher
└── README.md
```

---

## 4. Quick Start Guide

### Step 1: Ensure Ollama is running
Open PowerShell or Command Prompt:
```cmd
ollama run qwen3.5:9b
```

### Step 2: Launch VICTOR
Double click **`run_ui.bat`** or execute via terminal:
```cmd
.\.venv\Scripts\python.exe run_victor.py
```

### Step 3: Hands-Free Voice Operation
1. Victor starts in **STANDBY** mode with a gentle cyan pulsing core.
2. Say: **"Victor"**
3. Victor will chime and transition to **LISTENING** (vibrant green).
4. Speak your command:
   - *"Open Visual Studio Code"*
   - *"Take a screenshot"*
   - *"What is my CPU and GPU status?"*
   - *"Set system volume to 60 percent"*
   - *"Remember that I am designing an autonomous drone navigation system"*
   - *"What do you remember about my projects?"*
5. Victor executes the command, speaks the response through natural TTS, and returns to standby!

---

## 5. Keyboard Shortcuts & Controls

| Shortcut / Button | Function |
|---|---|
| **F11** | Toggle Full-Screen Holographic HUD |
| **Escape** | Stop Victor speaking immediately / Exit Full-Screen |
| **Enter** | Send text command from prompt input bar |
| **⚡ LOW POWER** | Switch to ultra-low CPU/GPU standby mode |
| **⚖ BALANCED** | Switch to moderate visual performance mode |
| **🚀 PERF** | Switch to full visual effects and animations |
| **🎙 Button** | Push-to-talk manual microphone activation |
| **🌙 Button** | Toggle standby sleep mode |
| **⏹ STOP** | Immediate speech interruption |

---

## 6. Resource Optimization Benchmarks

Measured on HP Victus 15 (Intel Core i7-13620H 16 Threads, 24GB DDR5, NVIDIA RTX 5060):

| Metric | Before Optimization | After Optimization (Low Power Mode) | Improvement |
|---|---|---|---|
| **Standby CPU Usage** | ~57.8% (unthrottled loops & `nvidia-smi`) | **0.0% – 0.5%** | **~99% reduction** |
| **Telemetry Overhead** | Spawning subprocess every 1.5s | **Cached (1.06 ms lookup)** | **Zero CPU spikes** |
| **Background Thread Count** | 41+ active threads | **10–11 threads** | **~73% thread reduction** |
| **Standby RAM Footprint** | ~806 MB | **~208 MB** (Whisper loaded on-demand) | **~74% memory reduction** |
| **Idle GPU VRAM** | 6.6 GB continuously held | **0 MB idle** (Ollama unloads model when idle) | **Full VRAM freed for games/apps** |
| **Speech Pause Tolerance** | 500ms fixed cutoff | **1.0s adaptive silence endpoint** | **No mid-sentence cutoffs** |
| **Concurrency Duplication** | Multiple responses possible | **Guaranteed 1 response per turn** | **Zero duplicate responses** |

---

## 7. Running Tests

Run the complete 9-point subsystem verification suite:
```cmd
.\.venv\Scripts\python.exe run_victor.py --test
```
or
```cmd
.\.venv\Scripts\python.exe tests\test_victor.py
```

---

## 7. Re-training Custom Wake Word

To re-calibrate or re-generate the custom ONNX model (`data/models/victor.onnx`) with different sensitivities or voice pitches:
```cmd
.\.venv\Scripts\python.exe run_victor.py --train
```
The script synthesizes positive samples of "Victor" across rates and voices, extracts 16x96 embeddings via openWakeWord's feature extractor, fits an MLP classifier with Scikit-Learn, and exports a production-ready ONNX model.
