# Panda Voice — Prerequisites & Environment Setup

**Last Updated:** 2026-06-08

This document covers everything you need before writing or running any code.

---

## 1. System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| macOS | 12 Monterey | 13+ Ventura / Sonoma / Sequoia |
| Python | 3.10 | 3.12 |
| RAM | 8GB | 16GB |
| Disk | 1GB free | 2GB free |
| CPU | Intel Core i5 | Apple Silicon M1+ (MPS acceleration) |

---

## 2. Homebrew Packages

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Required: PortAudio (needed by PyAudio for microphone access)
brew install portaudio

# Verify
brew info portaudio
```

---

## 3. Python Setup

```bash
# Check version (need 3.10+)
python3 --version

# If using pyenv
pyenv install 3.12.3
pyenv local 3.12.3

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install wheel first
pip install --upgrade pip wheel

# Pin setuptools for openai-whisper compatibility
pip install "setuptools<70"

# Install all dependencies
pip install -r requirements.txt
```

---

## 4. Python Dependencies

Full `requirements.txt` (including new Panda Voice deps):

```
# --- Existing whisper-flow deps ---
jiwer==3.0.4
pytest==7.3.2
black==23.3.0
pandas==3.0.1
httpx==0.27.0
pylint==3.0.3
PyAudio==0.2.14
fastapi==0.108.0
pytest-cov==4.1.0
pytest-timeout==2.3.1
pytest-asyncio==0.23.7
pytest-benchmark==4.0.0
websocket-client==1.8.0
python-multipart==0.0.9
openai-whisper==20250625
pylint-fail-under==0.3.0
uvicorn[standard]==0.30.1

# --- New Panda Voice deps ---
rumps>=0.4.0              # macOS menu bar app
pynput>=1.7.6             # Global hotkeys + keyboard simulation
pyperclip>=1.8.2          # Clipboard read/write
anthropic>=0.40.0         # Claude API client
```

**Note:** `rumps` is macOS only. If you need to run tests on Linux CI, mock `rumps` imports.

---

## 5. Whisper Model Download

The multilingual `base` model (~148MB) downloads automatically on first run to `~/.cache/whisper/base.pt`.

To pre-download manually:

```bash
source .venv/bin/activate
python3 -c "import whisper; whisper.load_model('base')"
```

Expected output:
```
100%|████████████████████| 148M/148M [00:30<00:00, 4.92MiB/s]
```

### Apple Silicon GPU Acceleration (MPS)

If you're on an M1/M2/M3/M4 Mac, Whisper will automatically use the Metal Performance Shaders (MPS) backend, significantly reducing transcription time.

Verify MPS is available:
```bash
python3 -c "import torch; print(torch.backends.mps.is_available())"
# Should print: True
```

---

## 6. macOS Permissions

These must be granted **before** running the app. The app will prompt on first launch, but you can also set them manually.

### 6.1 Microphone Access

`System Settings → Privacy & Security → Microphone`  
→ Enable for **Terminal** (or your IDE / Python launcher)

Test microphone access:
```bash
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
info = p.get_default_input_device_info()
print('Microphone found:', info['name'])
p.terminate()
"
```

### 6.2 Accessibility Access

Required for `pynput` to simulate keyboard input (Cmd+V paste).

`System Settings → Privacy & Security → Accessibility`  
→ Enable for **Terminal** (or your app launcher)

### 6.3 Input Monitoring

Required for `pynput` to detect global keystrokes (hotkey listening) while other apps are in focus.

`System Settings → Privacy & Security → Input Monitoring`  
→ Enable for **Terminal** (or your app launcher)

**Important:** After granting these permissions, restart Terminal for them to take effect.

---

## 7. Anthropic API Key

Only required for AI meeting note summarization. Voice input works without it.

```bash
# Option A: Environment variable (recommended for development)
export ANTHROPIC_API_KEY=sk-ant-...

# Option B: Config file (persists across sessions)
mkdir -p ~/.panda-voice
cat > ~/.panda-voice/config.json << 'EOF'
{
  "anthropic_api_key": "sk-ant-...",
  "hotkey": "<alt>+<space>",
  "model": "base",
  "language": "auto",
  "output_dir": "~/Documents/MeetingNotes",
  "restore_clipboard": true
}
EOF
chmod 600 ~/.panda-voice/config.json
```

---

## 8. Verify Full Setup

Run this checklist to confirm everything is ready before development:

```bash
source .venv/bin/activate

# 1. Python version
python3 --version
# Expected: Python 3.10.x or higher

# 2. PortAudio
python3 -c "import pyaudio; p=pyaudio.PyAudio(); print('PyAudio OK, devices:', p.get_device_count()); p.terminate()"
# Expected: PyAudio OK, devices: N (N > 0)

# 3. Whisper + model
python3 -c "import whisper; m=whisper.load_model('base'); print('Whisper OK:', type(m).__name__)"
# Expected: Whisper OK: Whisper

# 4. MPS (Apple Silicon only)
python3 -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
# Expected: MPS available: True  (False is OK on Intel, will use CPU)

# 5. rumps (macOS menu bar)
python3 -c "import rumps; print('rumps OK:', rumps.__version__)"
# Expected: rumps OK: 0.4.x

# 6. pynput
python3 -c "from pynput import keyboard; print('pynput OK')"
# Expected: pynput OK

# 7. pyperclip
python3 -c "import pyperclip; pyperclip.copy('test'); print('pyperclip OK:', pyperclip.paste())"
# Expected: pyperclip OK: test

# 8. anthropic
python3 -c "import anthropic; print('anthropic SDK OK:', anthropic.__version__)"
# Expected: anthropic SDK OK: 0.x.x

# 9. API key
python3 -c "
import os, anthropic
key = os.getenv('ANTHROPIC_API_KEY', '')
print('API key:', 'SET' if key.startswith('sk-') else 'NOT SET')
"
# Expected: API key: SET
```

---

## 9. Common Setup Issues

| Issue | Cause | Fix |
|---|---|---|
| `PyAudio` install fails | PortAudio not installed | `brew install portaudio` first |
| `OSError: [Errno -9996] Invalid input device` | Microphone permission not granted | System Settings → Privacy → Microphone → enable Terminal |
| `pynput` hotkey not detected | Input Monitoring permission missing | System Settings → Privacy → Input Monitoring → enable Terminal |
| `Cmd+V` doesn't paste | Accessibility permission missing | System Settings → Privacy → Accessibility → enable Terminal |
| `rumps` not found on import | Running on Linux | rumps is macOS-only; mock it for CI |
| `torch.backends.mps` error | Old PyTorch version | `pip install --upgrade torch` |
| Whisper model download fails | No internet / proxy | Pre-download manually or check connection |
| `setuptools` error during install | Too-new setuptools + openai-whisper | `pip install "setuptools<70"` before other deps |
