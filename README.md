
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
│   ├── train_victor_model.py # Automated synthetic training pipeline for 'Victor'
│   └── install_autostart.py  # Add/remove the tray launcher from Windows Startup
├── src/
│   ├── actions/
│   │   └── computer_control.py # Whitelist automation, pycaw volume, screenshots
│   ├── brain/
│   │   └── llm.py            # Ollama Qwen 3.5 9B conversation engine
│   ├── config/
│   │   └── settings.py       # Configuration manager singleton
│   ├── core/
│   │   ├── audio_effects.py  # Sci-Fi sound effect synthesizer
│   │   ├── hotkey.py         # Win32 global hotkeys (RegisterHotKey)
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
│   │   ├── tray.py           # No-window tray assistant (hotkeys + wake word)
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
This opens the animated HUD. The legacy multi-panel command center is still
available with `run_victor.py --classic`, and the tray-only mode with `--tray`.

### Step 3: Talk to VICTOR
1. The HUD opens with a slow cyan core (IDLE).
2. Press **Ctrl + Alt + V** or say **"Victor"**.
3. The core turns green and the waveform ring follows your voice (LISTENING).
4. Speak normally:
   - *"Open Visual Studio Code"*
   - *"What is my CPU and GPU status?"*
   - *"Remember that I am designing a drone navigation system"*
5. The core turns amber while VICTOR thinks, blue while it speaks, then it
   returns to LISTENING so you can keep the conversation going without pressing
   anything again.
6. Press **Esc** or **Ctrl + Alt + X** to interrupt speech, or click the core.
7. Silence for 8 seconds ends the turn; the HUD hides itself after 30 seconds of
   inactivity.

Every turn is transcribed on screen (YOU / VICTOR) and VICTOR speaks the answer.
There are no chimes, no notification popups, and only one VICTOR instance can
run: a second launch simply brings the running HUD forward.

### Step 4: Tray Mode — the no-window daily driver

For everyday use you do not need the full HUD. Tray mode keeps VICTOR resident
in the notification area with global hotkeys, and speaks everything back:

```cmd
.\.venv\Scripts\python.exe run_victor.py --tray
```

| Control | Action |
|---|---|
| **Ctrl + Alt + V** | Talk now (same as saying "Victor") |
| **Ctrl + Alt + T** | Type a command instead of speaking |
| **Ctrl + Alt + X** | Stop speaking / cancel the current turn |
| Left click tray icon | Talk now |
| Right click tray icon | Menu: wake word, spoken replies, power mode, HUD, log, autostart, quit |

Right-click menu extras: **Spoken replies** toggle, **Power mode** (low/balanced/
performance), **Open full HUD**, **Open log** (`logs/tray.log`), and **Start with
Windows** (writes a launcher to your Startup folder — no admin rights needed).

Start automatically at login from the command line instead:

```cmd
.\.venv\Scripts\python.exe run_victor.py --install-autostart
.\.venv\Scripts\python.exe run_victor.py --remove-autostart
```

Notes:
- Only one tray instance can run; a second launch exits silently (named mutex).
- Startup is quiet: the tray icon appears immediately, Whisper is lazy-loaded on
  the first spoken command, so idle RAM stays low.
- The wake-word listener discards its first ~2 s (ONNX buffer warm-up) and then
  de-bounces for 2 s, which removes the startup false trigger.
- Wake word too eager or too deaf? Tune `voice.wake_word_sensitivity` in
  `config/settings.json` (0.7 default, raise toward 0.85 in a noisy room).
  Hotkeys are unaffected by this setting.

---

## 5. Keyboard Shortcuts & Controls

HUD (default interface):

| Shortcut / Action | Function |
|---|---|
| **Ctrl + Alt + V** | Open the HUD and start listening (or interrupt if it is speaking) |
| **Ctrl + Alt + X** | Interrupt speech / cancel listening |
| **Escape** | Same as Ctrl + Alt + X |
| **Click the core** | Start talking, or interrupt the current answer |
| **CLOSE** | Quit VICTOR |
| **CLEAR** | Clear the on-screen transcript |
| **"Victor"** (wake word) | Open the HUD and start listening |

Legacy command center (`--classic`): **F11** full screen, **Escape** stop
speaking, **Enter** send typed command, power-mode and stop buttons in the
header. Tray mode (`--tray`): same hotkeys plus a right-click menu.

---

## 6. Resource Optimisation Benchmarks

Measured on this machine (Intel Core i7-13620H, 24 GB DDR5, NVIDIA RTX 5060,
Windows 11) with `scripts/measure_resources.py` and `scripts/bench_hud.py`.
Reproduce with:

```cmd
.\.venv\Scripts\python.exe scripts\bench_hud.py --seconds 20
.\.venv\Scripts\python.exe scripts\bench_hud.py --seconds 20 --hidden
.\.venv\Scripts\python.exe scripts\measure_resources.py --label "live HUD" --seconds 20
```

| Metric | Legacy command center (`--classic`) | New HUD | Notes |
|---|---|---|---|
| **RAM, visible and idle** | 919 MB peak | **307 MB** | working set, single process |
| **CPU, visible and animating** | 194.8% of all cores (12.2% of machine) | **10.5%** (0.7%) | no 60 fps animations |
| **CPU, HUD hidden** | n/a | **4.5%** (0.3%) | animation timer stops with the window |
| **CPU, listening / speaking animation** | n/a | **13.5% / 13.7%** (0.8% / 0.9%) | waveform driven at 25 fps |
| **Wake word listener** | same engine | **~16% of one core** (~1% of machine) | 80 ms ONNX frames, 1 thread |
| **Whisper while a turn is active** | same engine | **+~500 MB**, released after 5 min idle | `voice.idle_unload_seconds` |
| **GPU** | 0% | **0% idle** | HUD renders on the Intel iGPU; RTX stays free for Ollama |
| **Speech-to-text, 2 s clip** | ~19 s per turn | **~9.5 s** | explicit CTranslate2 threads + cached language |
| **LLM reply, warm model** | n/a | **~5-13 s** | `qwen3.5:9b` on GPU, `keep_alive=30m` |
| **Text to speech** | same engine | **real time (~180 wpm)** | blocks until audio finishes |

Notes:
- The wake word never sees VICTOR's own voice: the listener is paused while the
  microphone is held and while TTS is speaking.
- `keep_alive: "30m"` keeps the 9B model resident on the GPU between turns, so a
  conversation does not pay the ~6.6 GB reload cost.
- Speech-to-text is the slowest part on this CPU. It can be cut to ~3 s by
  setting `voice.stt_model` to `"base.en"` in `config/settings.json`, at the cost
  of Tamil/Tanglish accuracy.

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
