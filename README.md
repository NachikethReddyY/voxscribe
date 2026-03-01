# 🎙️ VoxScribe

**Local speech-to-text and AI-powered Smart Write for your desktop.**

VoxScribe runs silently in your system tray and gives you two superpowers via global hotkeys:

1. **Transcribe** — Press the hotkey, speak, press again. Your words appear as text at your cursor.
2. **Smart Write** — Same workflow, but an on-device LLM rewrites your speech into polished prose before pasting.

Everything runs **100% locally**. No cloud APIs. No data leaves your machine.

---

## ✨ Features

- **Local Whisper STT** — Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) for fast, accurate transcription.
- **Local LLM Rewriting** — Uses [Ollama](https://ollama.ai) to rephrase transcriptions with any model you choose.
- **Global Hotkeys** — System-wide shortcuts that work from any application.
- **Smart Injection** — Automatically pastes into the focused text field, or falls back to the clipboard.
- **Floating Overlay** — A minimal, translucent status indicator appears only when active.
- **Cross-Platform** — macOS and Windows (Linux support is experimental).
- **Lightweight** — No Electron. No web browser. Just Python and Qt.

---

## 📦 Installation

### Prerequisites

| Dependency | Purpose | Install |
|---|---|---|
| Python 3.10+ | Runtime | [python.org](https://python.org) |
| Ollama | Local LLM server (for Smart Write) | [ollama.ai](https://ollama.ai) |
| PortAudio | Audio capture backend | `brew install portaudio` (macOS) / bundled on Windows |

### Install VoxScribe

```bash
git clone https://github.com/yourusername/voxscribe.git
cd voxscribe
pip install -e .
```

### Pull an Ollama Model (for Smart Write)

```bash
ollama pull llama3.1:8b
```

---

## 🚀 Usage

### Start VoxScribe

```bash
voxscribe
```

A tray icon appears. The app is now listening for hotkeys.

### Default Hotkeys

| Action | macOS | Windows / Linux |
|---|---|---|
| **Transcribe** | `Ctrl+Shift+S` | `Ctrl+Shift+S` |
| **Smart Write** | `Ctrl+Shift+D` | `Ctrl+Shift+D` |

### Workflow

1. **Press the hotkey once** — Recording starts. A floating indicator appears.
2. **Speak naturally.**
3. **Press the same hotkey again** — Recording stops. Transcription (and optional rewriting) begins.
4. **Text is pasted** at your cursor, or copied to clipboard if no text field is focused.

---

## ⚙️ Configuration

Edit `settings.toml` (created on first run) in your project directory or `~/.config/voxscribe/settings.toml`:

```toml
[whisper]
model_path = "base.en"       # Or a path to a local CTranslate2 model
device = "auto"               # "auto", "cpu", or "cuda"
compute_type = "int8"         # "float16", "int8", "float32"
language = "en"

[ollama]
base_url = "http://127.0.0.1:11434"
model = "llama3.1:8b"
timeout_seconds = 60

[hotkeys]
transcribe = "<ctrl>+<shift>+s"
smart_write = "<ctrl>+<shift>+d"

[audio]
sample_rate = 16000
channels = 1
```

### Whisper Model Options

You can use any model size name that faster-whisper supports: `tiny`, `tiny.en`, `base`, `base.en`, `small`, `medium`, `large-v2`, `large-v3`. Alternatively, point `model_path` to a directory containing a CTranslate2-converted model.

---

## 🏗️ Architecture
┌─────────────┐     hotkey      ┌───────────────┐
│  pynput      │ ──────────────▶│  AudioRecorder │
│  GlobalHotKey│                │  (sounddevice) │
└─────────────┘                └───────┬───────┘
│ audio buffer
▼
┌───────────────┐
│  Transcriber   │
│ (faster-whisper)│
└───────┬───────┘
│ raw text
┌──────────────┼──────────────┐
│ transcribe   │              │ smart_write
▼              │              ▼
┌──────────┐         │      ┌──────────────┐
│ Injector │         │      │OllamaRewriter│
│(paste/   │         │      │  (httpx)     │
│clipboard)│         │      └──────┬───────┘
└──────────┘         │             │ polished text
│             ▼
│        ┌─────────┐
│        │ Injector │
│        └─────────┘
│
┌─────┴─────┐
│  Overlay   │  (PySide6 floating widget)
│  TrayIcon  │
└───────────┘

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

---

## 🙏 Acknowledgments

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Lightning-fast Whisper inference.
- [Ollama](https://ollama.ai) — Run LLMs locally with zero friction.
- [pynput](https://github.com/moses-palmer/pynput) — Cross-platform input monitoring.
- [PySide6](https://www.qt.io/qt-for-python) — The official Python bindings for Qt 6.
