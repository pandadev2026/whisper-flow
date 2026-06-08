# Panda Voice — Product Requirements Document

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2026-06-08

---

## 1. Overview

Panda Voice is a macOS menu bar application that converts speech to text in real time, enabling users to dictate into any application and automatically generate structured meeting notes. It runs entirely on-device for transcription (no audio leaves the machine), and optionally uses Claude API only for meeting notes summarization.

---

## 2. Problem Statement

| Pain Point | Current Workaround | Why It Falls Short |
|---|---|---|
| Typing is slow for extended sessions (coding, chatting with AI) | macOS built-in Dictation | Only works in supported apps, no push-to-talk, English-only quality |
| Meeting notes require attention away from the conversation | Manual note-taking during meetings | Misses content, cognitively expensive |
| Existing voice tools send audio to the cloud | Accept privacy risk | Unacceptable for sensitive meetings/work |

---

## 3. Users

**Primary — Developer / Knowledge Worker**
- Uses Claude Code, terminals, chat apps daily
- Attends 3-6 meetings per week
- Comfortable with macOS, basic CLI setup
- Wants to reduce typing without sacrificing privacy

**Secondary — Anyone who runs frequent meetings**
- Project manager, consultant, team lead
- Needs searchable, structured notes after every meeting
- Currently copy-pastes from Zoom transcripts or types manually

---

## 4. Goals & Non-Goals

### Goals (v1.0)
- Push-to-talk voice input that pastes text into any active app
- Meeting notes mode: continuous transcription → Claude-structured summary
- Full support for Chinese, English, and mixed Chinese-English
- All audio processing local (Whisper on-device)
- macOS menu bar app, zero UI friction

### Non-Goals (v1.0)
- Windows / Linux support
- Speaker diarization (who said what)
- Real-time streaming preview for push-to-talk
- Cloud sync or mobile companion app
- Custom vocabulary / hotwords
- Zoom / Teams API integration

---

## 5. Features

### 5.1 Voice Input — Push-to-Talk

**Trigger:** Hold `Option + Space` (configurable)  
**Flow:**
1. User holds hotkey → recording starts, menu bar icon turns 🔴
2. User speaks
3. User releases hotkey → transcription starts, icon turns ⏳
4. Raw transcript is polished by Claude API (if enabled), then pasted into the currently focused app
5. Original clipboard is restored, icon returns to 🎤

**Requirements:**
- Latency: ≤ 2s from key release to text appearing (for speech up to 15s)
- Language: auto-detect Chinese / English / mixed
- Audio format: 16 kHz, 16-bit, mono PCM
- Works in: terminal, browser text fields, chat apps, email, any focusable text input
- Visual feedback: menu bar icon reflects current state
- If transcription is empty (silence), do nothing and show brief notification

**Text Polishing (requires API key, configurable on/off):**
- Remove filler words: "um", "uh", "like", "you know", "啊", "嗯", "那个", etc.
- Fix grammar mistakes and awkward phrasing
- Edit for clarity and conciseness — preserve the user's meaning and tone, trim redundancy
- Do NOT rewrite or paraphrase beyond what's needed; output should still sound like the user
- If API key not set or polishing is disabled, paste raw Whisper transcript as-is

### 5.2 Meeting Notes Mode

**Trigger:** Click "Start Meeting" in menu bar  
**Flow:**
1. Recording begins; menu bar shows 🔴 REC with elapsed timer
2. Audio is captured in chunks and transcribed continuously via streaming
3. Each finalized transcript segment is appended to a temp `.txt` file in real time
4. User clicks "Stop & Save Notes" in menu bar
5. Full transcript is sent to Claude Sonnet for structured summarization
6. Structured Markdown notes are saved to `~/Documents/MeetingNotes/YYYY-MM-DD_HH-MM.md`
7. macOS notification shown; Finder reveals the file

**Meeting Notes Output Format:**
```markdown
# Meeting Notes — 2026-06-08 14:30

## Summary
[2-3 sentence overview of what was discussed]

## Topics Discussed
- Topic 1
- Topic 2

## Decisions Made
- Decision 1
- Decision 2

## Action Items
- [ ] Action item 1 — Owner (if mentioned)
- [ ] Action item 2

## Raw Transcript
[Full verbatim transcript, timestamped by segment]
```

**Requirements:**
- Minimum session length: 30 seconds
- Transcript auto-saved in real time (no data loss if app crashes)
- Claude API call only happens at the end (not during recording)
- If no API key configured, save raw transcript only with a note to summarize later
- Max meeting duration: 3 hours (after which a warning is shown)

### 5.3 Menu Bar UI

**States and icons:**

| State | Icon | Menu Label |
|---|---|---|
| Idle | 🎤 | "Panda Voice" |
| Recording (push-to-talk) | 🔴 | "Recording…" |
| Transcribing | ⏳ | "Transcribing…" |
| Meeting active | 🔴 REC 00:05:23 | "Meeting in Progress" |
| Summarizing | ✨ | "Generating Notes…" |

**Menu items:**
```
🎤 Panda Voice
─────────────────
Voice Input: ON / OFF
Start Meeting / Stop & Save Notes
─────────────────
Last Notes: Open Folder
─────────────────
Settings...
  ├─ Hotkey: Option+Space [change]
  ├─ Model: base / small / medium
  └─ API Key: configured ✓
─────────────────
Quit
```

### 5.4 Configuration

Stored in `~/.panda-voice/config.json`:

| Key | Default | Description |
|---|---|---|
| `hotkey` | `<alt>+<space>` | Push-to-talk key combo |
| `model` | `base` | Whisper model: tiny / base / small / medium |
| `language` | `auto` | Force language or auto-detect |
| `output_dir` | `~/Documents/MeetingNotes` | Where meeting notes are saved |
| `anthropic_api_key` | `""` | Claude API key (or read from env) |
| `restore_clipboard` | `true` | Restore clipboard after paste |
| `polish_text` | `true` | Use Claude API to clean up filler words and fix grammar before pasting |

---

## 6. Accuracy & Performance Targets

| Metric | Target | Notes |
|---|---|---|
| Voice input latency (≤10s speech) | ≤ 1.5s | From key release to paste |
| Voice input latency (10-30s speech) | ≤ 3s | Longer speech, more processing |
| Meeting transcription WER (English) | ≤ 10% | Using whisper-base |
| Meeting transcription WER (Chinese) | ≤ 15% | Using whisper-base |
| App memory footprint (idle) | ≤ 300 MB | Whisper model loaded |
| App memory footprint (active) | ≤ 600 MB | |

---

## 7. Privacy & Security

- Microphone audio is **never sent to any server** during transcription
- Only the **final text transcript** (not audio) is sent to Claude API for meeting note summarization
- API key stored in local config file (`~/.panda-voice/config.json`, chmod 600)
- No analytics, no telemetry, no network calls except Claude API on meeting end

---

## 8. Constraints & Assumptions

- macOS only (menu bar app, Accessibility APIs, Cmd+V injection)
- Requires user to grant: Microphone, Accessibility, Input Monitoring permissions
- Whisper `base` model auto-downloads on first run (~148MB via `openai-whisper`)
- Internet connection required only for Claude API summarization step
- Push-to-talk max duration: 60 seconds per activation (prevents accidental long recordings)
