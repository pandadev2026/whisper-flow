import logging
import threading

import rumps

import whisperflow.transcriber as ts
from panda_voice import polisher, summarizer
from panda_voice.config import Config
from panda_voice.hotkey import HotkeyManager
from panda_voice.injector import paste_text
from panda_voice.meeting import MeetingRecorder
from panda_voice.recorder import Recorder
from panda_voice.state import STATE_ICONS, AppState

logger = logging.getLogger(__name__)


class PandaVoiceApp(rumps.App):
    def __init__(self, model):
        super().__init__(STATE_ICONS[AppState.IDLE], quit_button="Quit")
        self.config = Config()
        self.state = AppState.IDLE
        self.model = model
        self.recorder = Recorder()
        self._meeting: MeetingRecorder | None = None

        self._menu_start_meeting = rumps.MenuItem("Start Meeting", callback=self._start_meeting)
        self._menu_stop_meeting = rumps.MenuItem("Stop Meeting", callback=self._stop_meeting)
        self._menu_stop_meeting.set_callback(None)  # disabled initially

        self.menu = [
            rumps.MenuItem("Option+Space to dictate"),
            None,
            self._menu_start_meeting,
            self._menu_stop_meeting,
            None,
        ]

        self.hotkey = HotkeyManager(
            on_activate=self._on_hotkey_down,
            on_deactivate=self._on_hotkey_up,
        )
        self.hotkey.start()

    # ── PTT ──────────────────────────────────────────────────────────────────

    def _set_state(self, state: AppState):
        self.state = state
        self.title = STATE_ICONS[state]

    def _on_hotkey_down(self):
        if self.state != AppState.IDLE:
            return
        self._set_state(AppState.RECORDING)
        self.recorder.start()

    def _on_hotkey_up(self):
        if self.state != AppState.RECORDING:
            return
        chunks = self.recorder.stop()
        self._set_state(AppState.TRANSCRIBING)
        threading.Thread(target=self._process, args=(chunks,), daemon=True).start()

    def _process(self, chunks):
        try:
            if not chunks:
                return
            lang = None if self.config.language == "auto" else self.config.language
            result = ts.transcribe_pcm_chunks(self.model, chunks, lang=lang)
            text = result.get("text", "").strip()
            if not text:
                return
            backend = self.config.polish_backend
            if backend == "minimax" and self.config.minimax_api_key and len(text.split()) >= 3:
                text = polisher.minimax_polish(
                    text,
                    api_key=self.config.minimax_api_key,
                    group_id=self.config.minimax_group_id,
                    model=self.config.minimax_model,
                    base_url=self.config.minimax_url,
                )
            elif backend == "claude" and self.config.anthropic_api_key:
                text = polisher.claude_polish(text, api_key=self.config.anthropic_api_key)
            paste_text(text, restore_clipboard=self.config.restore_clipboard)
        except Exception as e:
            logger.error("Processing error: %s", e)
        finally:
            self._set_state(AppState.IDLE)

    # ── Meeting ───────────────────────────────────────────────────────────────

    def _start_meeting(self, _):
        if self.state != AppState.IDLE:
            rumps.alert("Panda Voice", "Finish current action before starting a meeting.")
            return
        self._set_state(AppState.MEETING)
        self._menu_start_meeting.set_callback(None)
        self._menu_stop_meeting.set_callback(self._stop_meeting)
        self._meeting = MeetingRecorder(self.model, self.config)
        self._meeting.start()
        rumps.notification("Panda Voice", "Meeting started", "Recording… click Stop Meeting when done.")

    def _stop_meeting(self, _):
        if self.state != AppState.MEETING or self._meeting is None:
            return
        self._set_state(AppState.SUMMARIZING)
        self._menu_stop_meeting.set_callback(None)
        meeting = self._meeting
        self._meeting = None
        threading.Thread(target=self._finalize_meeting, args=(meeting,), daemon=True).start()

    def _finalize_meeting(self, meeting: MeetingRecorder):
        try:
            segments = meeting.stop()
            if not segments:
                rumps.notification("Panda Voice", "Meeting ended", "No speech detected.")
                return
            path = summarizer.summarize(
                segments,
                output_dir=self.config.output_dir,
                api_key=self.config.anthropic_api_key,
                ollama_model=self.config.ollama_model,
                ollama_url=self.config.ollama_url,
            )
            rumps.notification("Panda Voice", "Meeting notes saved", path)
        except Exception as e:
            logger.error("Meeting finalization error: %s", e)
            rumps.notification("Panda Voice", "Error generating notes", str(e))
        finally:
            self._set_state(AppState.IDLE)
            self._menu_start_meeting.set_callback(self._start_meeting)
