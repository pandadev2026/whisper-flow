# Panda Voice

Real-time voice-to-text for macOS — dictate into any app and automatically generate meeting notes.

Built on top of [whisper-flow](https://github.com/dimastatz/whisper-flow) with OpenAI Whisper running fully on-device.

---

## What It Does

**Voice Input (Push-to-Talk)**  
Hold `Option+Space`, speak, release → transcribed text is instantly pasted into whatever app you're in. Works in terminals, browsers, chat apps, editors — anywhere.

**Meeting Notes**  
Start a meeting recording from the menu bar. When you stop, Claude automatically structures the full transcript into a clean Markdown file with summary, topics, decisions, and action items.

**Privacy First**  
Your audio never leaves your machine. Transcription runs locally via Whisper. Only the final text transcript is sent to Claude API (only for meeting note summarization, and only if you choose to use it).

---

## Supported Languages

Chinese, English, and mixed Chinese-English (auto-detected).

---

## Requirements

- macOS 12 Monterey or later
- Python 3.10+
- [Homebrew](https://brew.sh) (for PortAudio)
- Anthropic API key (optional — only needed for AI meeting note summarization)

### macOS Permissions Required

You will be prompted to grant these on first launch:

| Permission | Why |
|---|---|
| **Microphone** | To capture your voice |
| **Accessibility** | To simulate Cmd+V for text injection |
| **Input Monitoring** | To detect the global hotkey while other apps are focused |

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/pandadev2026/whisper-flow.git panda-voice
cd panda-voice

# 2. Install PortAudio (required for PyAudio)
brew install portaudio

# 3. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Configure your API key (optional, for meeting notes)
export ANTHROPIC_API_KEY=your_key_here
# Or add it permanently:
echo '{"anthropic_api_key": "your_key_here"}' > ~/.panda-voice/config.json

# 5. Launch the app
python launch.py
```

The Whisper `base` model (~148MB) will be downloaded automatically on first run.

---

## Usage

### Voice Input

1. Make sure the Panda Voice menu bar icon (🎤) is visible
2. Click in any text field in any app
3. Hold `Option + Space`
4. Speak
5. Release — your words appear at the cursor

### Meeting Notes

1. Click the 🎤 menu bar icon
2. Select **Start Meeting**
3. The icon changes to 🔴 with a running timer
4. When done, click **Stop & Save Notes**
5. Your structured notes are saved to `~/Documents/MeetingNotes/` and a notification appears

### Configuration

```bash
# Default config location
~/.panda-voice/config.json
```

```json
{
  "hotkey": "<alt>+<space>",
  "model": "base",
  "language": "auto",
  "output_dir": "~/Documents/MeetingNotes",
  "anthropic_api_key": "",
  "restore_clipboard": true
}
```

Available models (tradeoff: speed vs accuracy):

| Model | Size | Speed | Languages |
|---|---|---|---|
| `tiny` | 74MB | Fastest | Multilingual |
| `base` | 148MB | Fast (default) | Multilingual |
| `small` | 488MB | Moderate | Multilingual |
| `medium` | 1.5GB | Slow | Multilingual |

---

## Project Structure

```
panda-voice/
├── panda_voice/          Application code
│   ├── app.py            Menu bar app
│   ├── hotkey.py         Global hotkey listener
│   ├── recorder.py       Microphone capture
│   ├── injector.py       Text injection
│   ├── meeting.py        Meeting session management
│   ├── notes_generator.py Claude API summarization
│   ├── state.py          App state machine
│   └── config.py         Configuration
├── whisperflow/          Transcription engine (whisper-flow)
├── docs/
│   ├── prd.md            Product Requirements Document
│   ├── architecture.md   System Architecture
│   └── roadmap.md        Roadmap
├── launch.py             Entry point
└── requirements.txt      Dependencies
```

---

## Development

```bash
# Run tests
./run.sh -test

# Run just the transcription server (original whisper-flow)
./run.sh -run-server
```

---

## Roadmap

- **Phase 1** — Push-to-talk voice input (dictate into any app)
- **Phase 2** — Meeting notes mode with Claude summarization
- **Phase 3** — Polish: permissions wizard, model selector, silence detection
- **Phase 4** — Speaker diarization, system audio capture, app bundle distribution

See [docs/roadmap.md](docs/roadmap.md) for full details.

---

## Based On

This project is built on top of [whisper-flow](https://github.com/dimastatz/whisper-flow) by [@dimastatz](https://github.com/dimastatz), which provides the real-time Whisper streaming transcription engine.
