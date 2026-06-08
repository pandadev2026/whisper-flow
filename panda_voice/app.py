import logging
import threading

import rumps

import whisperflow.transcriber as ts
from panda_voice import polisher
from panda_voice.config import Config
from panda_voice.hotkey import HotkeyManager
from panda_voice.injector import paste_text
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

        self.menu = [
            rumps.MenuItem("Option+Space to dictate"),
            None,
        ]

        self.hotkey = HotkeyManager(
            on_activate=self._on_hotkey_down,
            on_deactivate=self._on_hotkey_up,
        )
        self.hotkey.start()

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
            if self.config.polish_text and self.config.polish_backend == "ollama":
                text = polisher.polish(
                    text,
                    model=self.config.ollama_model,
                    base_url=self.config.ollama_url,
                )
            paste_text(text, restore_clipboard=self.config.restore_clipboard)
        except Exception as e:
            logger.error("Processing error: %s", e)
        finally:
            self._set_state(AppState.IDLE)
