# Panda Voice — Architecture

**Version:** 1.0  
**Last Updated:** 2026-06-08

---

## 1. System Overview

Panda Voice is a single-process macOS menu bar application. All audio processing runs in-process on the local machine. There is no server, no daemon, and no network traffic except the optional Claude API call at the end of a meeting session.

```
┌──────────────────────────────────────────────────────────────────┐
│                        macOS System                              │
│                                                                  │
│  Keyboard Events ──────► HotkeyManager                          │
│  Microphone ───────────► Recorder                               │
│  Active App ◄──────────── Injector                              │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                   Panda Voice Process                     │   │
│  │                                                           │   │
│  │  ┌────────────┐   ┌─────────────┐   ┌─────────────────┐  │   │
│  │  │  Menu Bar  │   │   Hotkey    │   │  State Manager  │  │   │
│  │  │  (rumps)   │◄──│   Manager   │──►│  IDLE/REC/TRANS │  │   │
│  │  └────────────┘   │  (pynput)   │   └────────┬────────┘  │   │
│  │                   └─────────────┘            │           │   │
│  │                                              │           │   │
│  │                         ┌────────────────────┤           │   │
│  │                         │                    │           │   │
│  │                    [PTT mode]          [Meeting mode]    │   │
│  │                         │                    │           │   │
│  │                         ▼                    ▼           │   │
│  │                  ┌─────────────┐   ┌──────────────────┐  │   │
│  │                  │  Recorder   │   │ MeetingManager   │  │   │
│  │                  │  (PyAudio)  │   │ (PyAudio stream) │  │   │
│  │                  └──────┬──────┘   └────────┬─────────┘  │   │
│  │                         │                   │            │   │
│  │                         ▼                   ▼            │   │
│  │                  ┌──────────────────────────────────┐    │   │
│  │                  │    WhisperFlow Transcription      │    │   │
│  │                  │    Engine (whisperflow/)          │    │   │
│  │                  │    Model: whisper-base (148MB)    │    │   │
│  │                  └──────────┬───────────────────────┘    │   │
│  │                             │                            │   │
│  │                  ┌──────────┴──────────┐                 │   │
│  │                  │                     │                 │   │
│  │                  ▼                     ▼                 │   │
│  │           ┌────────────┐     ┌──────────────────┐        │   │
│  │           │  Injector  │     │  NotesGenerator  │        │   │
│  │           │(clipboard  │     │ (Claude Sonnet)  │        │   │
│  │           │ + Cmd+V)   │     │                  │        │   │
│  │           └────────────┘     └────────┬─────────┘        │   │
│  │                                       │                  │   │
│  └───────────────────────────────────────┼──────────────────┘   │
│                                          │                      │
│                                          ▼                      │
│                              ~/Documents/MeetingNotes/          │
└──────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼ (notes summary only)
                                    Claude API (Anthropic)
```

---

## 2. Component Breakdown

### 2.1 Menu Bar App — `panda_voice/app.py`

**Responsibility:** Top-level application controller. Owns the `rumps.App` instance, responds to menu clicks, and delegates to other components.

**Key interfaces:**
- Receives state change events from `StateManager`
- Updates menu bar icon and menu items accordingly
- Spawns background thread for the asyncio event loop (rumps uses the main thread)

**Design decision:** `rumps` runs on the main thread. All audio/transcription work runs in a dedicated `asyncio` event loop on a background thread. Communication between them uses thread-safe `queue.Queue`.

### 2.2 Hotkey Manager — `panda_voice/hotkey.py`

**Responsibility:** Listen for global keyboard shortcuts and notify the app of key-down / key-up events.

**Library:** `pynput.keyboard.Listener`  
**Default hotkey:** `Option + Space` (`<alt>+<space>`)

**Push-to-talk logic:**
- `on_press(Option+Space)` → send `START_RECORDING` event if state is IDLE
- `on_release(Option+Space)` → send `STOP_RECORDING` event if state is RECORDING

**Requires:** macOS Accessibility permission + Input Monitoring permission

### 2.3 Recorder — `panda_voice/recorder.py`

**Responsibility:** Capture microphone audio and buffer it as raw PCM chunks.

**Audio spec:** 16 kHz, 16-bit signed int, mono (required by Whisper)  
**Chunk size:** 1024 frames (~64ms per chunk)

**Two operation modes:**

| Mode | Behavior |
|---|---|
| **PTT (Push-to-Talk)** | Collects all chunks in a list while key is held. On stop, returns full buffer for batch transcription. |
| **Meeting (Streaming)** | Continuously puts chunks into a `Queue`. Consumer (MeetingManager) drains the queue and feeds to the streaming transcriber. |

### 2.4 Transcription Engine — `whisperflow/transcriber.py` (existing)

**Responsibility:** Convert PCM audio to text using OpenAI Whisper.

**Model:** `base` (multilingual, 148MB) — replaces the existing `tiny.en.pt`  
**Language:** `auto` by default; detects Chinese, English, mixed automatically

**Two modes used:**
- **Batch** (PTT): `transcribe_pcm_chunks(model, chunks, lang="auto")` — one call, full buffer
- **Streaming** (Meeting): `TranscribeSession` from `whisperflow/streaming.py` — tumbling window

**Model loading:** Cached in `whisperflow/transcriber.py:models` dict. Loaded once on startup, kept in memory.

### 2.5 Injector — `panda_voice/injector.py`

**Responsibility:** Insert transcribed text into the currently focused application.

**Strategy:**
1. Save current clipboard content
2. Copy transcribed text to clipboard via `pyperclip`
3. Simulate `Cmd+V` via `pynput.keyboard.Controller`
4. Wait 100ms for paste to complete
5. Restore original clipboard content

**Why not type character by character?** Typing via `pynput` is slow (one keystroke at a time) and breaks with Chinese characters. Clipboard paste is instant and universal.

**Edge case:** If focus changes between key release and paste (user switches apps), text still pastes into whatever is focused. This is acceptable behavior.

### 2.6 Meeting Manager — `panda_voice/meeting.py`

**Responsibility:** Orchestrate continuous recording, real-time transcript accumulation, and final note generation.

**State:**
```python
@dataclass
class MeetingSession:
    start_time: datetime
    transcript_segments: list[dict]  # {text, timestamp, is_partial}
    temp_file: Path                  # rolling save
    duration: float
```

**Transcript accumulation:** Only `is_partial=False` segments are written to the temp file and included in the final notes.

**On stop:**
1. Signal `TranscribeSession` to stop
2. Flush remaining transcript to temp file
3. Build full transcript string
4. Call `NotesGenerator.generate(transcript)` if API key configured
5. Write final Markdown file
6. Show macOS notification

### 2.7 Notes Generator — `panda_voice/notes_generator.py`

**Responsibility:** Call Claude API to transform raw transcript into structured meeting notes.

**Model:** `claude-sonnet-4-6`  
**Input:** Full transcript text (plain text)  
**Output:** Structured Markdown (see PRD §5.2 for format)

**Prompt strategy:** Single-turn, no streaming needed. Transcript is sent in `user` turn. System prompt instructs Claude to produce structured notes in the specified format, preserving language (Chinese output for Chinese meetings, English for English, mixed as appropriate).

**Failure handling:** If Claude API call fails, save raw transcript with a header note: `[AI summary unavailable — raw transcript below]`

### 2.8 Config Manager — `panda_voice/config.py`

**Responsibility:** Load, validate, and persist user configuration.

**Location:** `~/.panda-voice/config.json`  
**API key fallback:** If not in config, reads `ANTHROPIC_API_KEY` environment variable.

---

## 3. Threading Model

```
Main Thread (macOS / rumps)
    │
    ├── rumps event loop (menu clicks, timer updates)
    └── Sends events → thread-safe Queue

Background Thread (asyncio event loop)
    │
    ├── pynput hotkey listener
    ├── PyAudio recording coroutines
    ├── whisperflow transcription tasks
    └── Claude API call (async httpx)

Communication: queue.Queue (thread-safe) between main and background
```

**Why a background asyncio thread?**  
`rumps` blocks the main thread. All our I/O (microphone, transcription, API) is async. We run `asyncio.run()` in a `threading.Thread` so both can coexist without blocking each other.

---

## 4. Data Flow

### 4.1 Push-to-Talk

```
[User holds Option+Space]
        │
        ▼
HotkeyManager.on_press()
        │
        ▼
StateManager → RECORDING
Recorder.start() → buffers PCM chunks
        │
[User releases Option+Space]
        │
        ▼
HotkeyManager.on_release()
        │
        ▼
Recorder.stop() → returns List[bytes]
        │
        ▼
transcriber.transcribe_pcm_chunks(model, chunks, lang="auto")
        │
        ▼
StateManager → IDLE
Injector.paste(text)  →  active app receives text
```

### 4.2 Meeting Notes

```
[User clicks "Start Meeting"]
        │
        ▼
MeetingManager.start()
        │
        ▼
Recorder starts streaming → Queue
        │
        ▼ (continuous loop)
TranscribeSession drains Queue
→ partial results discarded
→ final segments appended to temp file + in-memory list
        │
[User clicks "Stop & Save Notes"]
        │
        ▼
MeetingManager.stop()
        │
        ▼
Full transcript assembled
        │
        ├── [API key present] → NotesGenerator.generate(transcript)
        │                              │
        │                              ▼
        │                       Claude Sonnet API
        │                              │
        │                              ▼
        │                       Structured Markdown
        │
        └── [No API key] → Raw transcript only
                │
                ▼
        Save to ~/Documents/MeetingNotes/YYYY-MM-DD_HH-MM.md
        macOS notification
```

---

## 5. File Structure

```
panda-voice-control/
│
├── panda_voice/                    ← New: our application
│   ├── __init__.py
│   ├── app.py                      Menu bar app (rumps)
│   ├── hotkey.py                   Global hotkey listener (pynput)
│   ├── recorder.py                 Microphone capture (PyAudio)
│   ├── injector.py                 Text injection via clipboard
│   ├── meeting.py                  Meeting session orchestration
│   ├── notes_generator.py          Claude API summarization
│   ├── state.py                    App state enum + manager
│   └── config.py                   Config load/save
│
├── whisperflow/                    ← Existing: transcription engine
│   ├── transcriber.py              (modify: support base multilingual model)
│   ├── streaming.py                (reuse as-is)
│   ├── fast_server.py              (keep for standalone server use)
│   ├── audio/microphone.py         (keep, not used by our app directly)
│   └── models/
│       └── tiny.en.pt              (keep; new base model downloads to ~/.cache/whisper/)
│
├── tests/                          ← Existing + new tests
│   ├── panda_voice/
│   │   ├── test_recorder.py
│   │   ├── test_injector.py
│   │   └── test_meeting.py
│   └── ...existing tests...
│
├── docs/
│   ├── prd.md                      This product's PRD
│   ├── architecture.md             This file
│   ├── roadmap.md                  Roadmap
│   └── ...existing docs...
│
├── launch.py                       Entry point: python launch.py
├── requirements.txt                (updated with new deps)
├── README.md                       (updated for Panda Voice)
└── run.sh                          (updated with -app command)
```

---

## 6. Key Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Menu bar framework | `rumps` | Lightest macOS menu bar library, pure Python, actively maintained |
| Global hotkey | `pynput` | Cross-platform API, push-to-talk (key-down/up events), well-tested on macOS |
| Text injection | Clipboard + Cmd+V | Works universally across all apps incl. terminals; faster than simulated typing; handles Unicode/CJK correctly |
| Transcription | Whisper `base` (multilingual) | Best speed/accuracy tradeoff for Chinese+English; auto language detection; runs on Apple Silicon MPS |
| Meeting notes AI | Claude `claude-sonnet-4-6` | Best instruction-following for structured output; user already has API key |
| Async threading | Background asyncio thread | rumps owns main thread; keeps audio pipeline fully async without blocking UI |
| Model acceleration | MPS (Apple Silicon) / CPU | `torch.backends.mps.is_available()` check; significant speedup on M-series chips |
