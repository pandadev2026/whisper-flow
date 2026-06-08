# Panda Voice — Roadmap

**Last Updated:** 2026-06-08

---

## Current Status

| Component | Status |
|---|---|
| Whisper transcription engine | ✅ Inherited from whisper-flow |
| Streaming session management | ✅ Inherited from whisper-flow |
| macOS menu bar app | 🔲 Not started |
| Push-to-talk voice input | 🔲 Not started |
| Meeting notes mode | 🔲 Not started |
| Claude API integration | 🔲 Not started |

---

## Phase 1 — Core Voice Input MVP

**Goal:** Press a key, say something, have it appear in any app. Nothing else.  
**Target:** ~1 week

### Tasks
- [ ] Set up new `panda_voice/` module structure
- [ ] `config.py` — load/save `~/.panda-voice/config.json`
- [ ] `state.py` — app state enum (IDLE, RECORDING, TRANSCRIBING)
- [ ] `recorder.py` — PTT audio buffer (PyAudio, 16kHz mono)
- [ ] `hotkey.py` — global `Option+Space` listener via pynput
- [ ] `injector.py` — clipboard-based text injection + Cmd+V simulation
- [ ] `app.py` — rumps menu bar with state-reactive icon
- [ ] `launch.py` — entry point
- [ ] Update `requirements.txt` with new deps
- [ ] Update `whisperflow/transcriber.py` to support multilingual `base` model + Apple Silicon MPS
- [ ] Manual test: dictate into Claude Code terminal ✓
- [ ] Manual test: dictate into browser text field ✓
- [ ] Manual test: dictate Chinese into Notes app ✓

### Acceptance Criteria
- Hold `Option+Space`, speak 10 seconds of English → text pasted within 2s of release
- Hold `Option+Space`, speak 10 seconds of Chinese → text pasted within 2.5s of release
- App shows correct icon state (🎤 → 🔴 → ⏳ → 🎤)
- App does not crash on empty recording (silence only)

---

## Phase 2 — Meeting Notes Mode

**Goal:** Record a full meeting, get structured notes on stop.  
**Target:** ~1 week after Phase 1

### Tasks
- [ ] `meeting.py` — MeetingSession dataclass + start/stop orchestration
- [ ] Integrate `whisperflow/streaming.py` TranscribeSession for continuous mode
- [ ] Rolling transcript save to temp file (crash-safe)
- [ ] Meeting timer display in menu bar (🔴 REC 00:05:23)
- [ ] `notes_generator.py` — Claude Sonnet API call with structured prompt
- [ ] Prompt engineering: Chinese/English/mixed language output matching input
- [ ] Save final Markdown to `~/Documents/MeetingNotes/`
- [ ] macOS notification on completion (with "Open File" action button)
- [ ] Graceful fallback: no API key → save raw transcript only
- [ ] Manual test: 10-minute English meeting simulation ✓
- [ ] Manual test: 10-minute Chinese meeting simulation ✓

### Acceptance Criteria
- Start meeting → speak for 5 min → stop → structured notes file created within 30s
- Notes contain: Summary, Topics, Decisions, Action Items, Raw Transcript
- App continues to work (no crash) if internet unavailable during summarization
- Raw transcript saved even if Claude API call fails

---

## Phase 3 — Polish & Reliability

**Goal:** Production-quality app that stays out of the way.  
**Target:** ~1 week after Phase 2

### Tasks
- [ ] Onboarding wizard: auto-detect missing permissions (Accessibility, Mic, Input Monitoring) and guide user to grant them
- [ ] Settings panel in menu bar: change hotkey, select model size, set API key
- [ ] Silence detection: skip transcription if audio chunk is below silence threshold (reuse `whisperflow/audio/microphone.py:is_silent`)
- [ ] PTT max duration warning: alert at 55s, auto-stop at 60s
- [ ] Model size selector: tiny / base / small (with size/speed tradeoff shown)
- [ ] "Last Notes" submenu: quick-open last 5 meeting note files
- [ ] Auto-launch at login option
- [ ] App icon (proper macOS `.icns`)
- [ ] Basic error handling: mic in use by another app, model load failure

### Acceptance Criteria
- Fresh install on a new Mac works end-to-end with guided setup
- No crashes in 8-hour continuous idle (memory stable)
- Silence-only PTT activation produces no output and no error

---

## Phase 4 — Advanced Features (Future)

These are not committed to a timeline. They depend on user feedback from Phases 1-3.

### Voice Input Enhancements
- Streaming preview: show partial transcription in a small floating overlay before pasting
- App-aware mode: detect frontmost app and apply formatting (e.g., add `\n` after sentences in terminal mode)
- Custom hotkey configuration via UI
- Multi-language per-session lock (force Chinese or English instead of auto-detect)

### Meeting Notes Enhancements
- Speaker diarization: detect speaker changes and label segments (Speaker A, Speaker B)
- Zoom / Google Meet audio capture: tap system audio instead of microphone (requires virtual audio device)
- Export integrations: save to Notion page, Obsidian vault, or Markdown directory
- Meeting search: full-text search across all saved meeting notes

### Distribution
- Package as a standalone `.app` bundle (PyInstaller or py2app) — no Python required
- Homebrew tap for easy install: `brew install --cask panda-voice`
- Auto-update mechanism

---

## Known Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| macOS permission prompt blocks hotkey on first launch | High | Onboarding wizard in Phase 3 detects and guides |
| Whisper `base` model too slow on older Intel Macs | Medium | Offer `tiny` model fallback; document CPU requirements |
| pynput conflicts with other global hotkey apps | Low | Configurable hotkey; document known conflicts |
| Claude API rate limits during long meeting summarization | Low | Transcript is a single request; well within limits |
| PyAudio installation fails on certain macOS versions | Medium | `brew install portaudio` in setup; clear error message |
