import logging
import subprocess
import threading
import time
from pathlib import Path

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

PTT_WARN_SECS = 55
PTT_MAX_SECS = 60


class PandaVoiceApp(rumps.App):
    def __init__(self, model):
        super().__init__(STATE_ICONS[AppState.IDLE], quit_button="Quit")
        self.config = Config()
        self.state = AppState.IDLE
        self.model = model
        self.recorder = Recorder()
        self._meeting: MeetingRecorder | None = None
        self._timer_stop: threading.Event | None = None
        self._ptt_stop: threading.Event | None = None

        self._menu_start_meeting = rumps.MenuItem("Start Meeting", callback=self._start_meeting)
        self._menu_stop_meeting = rumps.MenuItem("Stop Meeting", callback=self._stop_meeting)
        self._menu_stop_meeting.set_callback(None)

        self._menu_last_notes = rumps.MenuItem("Last Notes")
        self._menu_open_folder = rumps.MenuItem("Open Notes Folder", callback=self._open_notes_folder)

        self._menu_settings = self._build_settings_menu()

        self.menu = [
            rumps.MenuItem("Hold left Option to dictate"),
            None,
            self._menu_start_meeting,
            self._menu_stop_meeting,
            None,
            self._menu_last_notes,
            self._menu_open_folder,
            None,
            self._menu_settings,
            None,
        ]

        self._refresh_last_notes()

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
        self._ptt_stop = threading.Event()
        threading.Thread(target=self._ptt_watchdog, args=(self._ptt_stop,), daemon=True).start()

    def _ptt_watchdog(self, stop: threading.Event):
        if not stop.wait(PTT_WARN_SECS):
            rumps.notification("Panda Voice", "Still recording…", "Auto-stopping in 5 seconds.")
        if not stop.wait(PTT_MAX_SECS - PTT_WARN_SECS):
            logger.info("PTT max duration reached — auto-stopping")
            self._on_hotkey_up()

    def _on_hotkey_up(self):
        if self._ptt_stop:
            self._ptt_stop.set()
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
            if self.config.polish_text and len(text.split()) >= 3:
                if backend == "minimax" and self.config.minimax_api_key:
                    text = polisher.minimax_polish(
                        text,
                        api_key=self.config.minimax_api_key,
                        group_id=self.config.minimax_group_id,
                        model=self.config.minimax_model,
                        base_url=self.config.minimax_url,
                    )
                elif backend == "claude" and self.config.anthropic_api_key:
                    text = polisher.claude_polish(text, api_key=self.config.anthropic_api_key)
                elif backend == "ollama":
                    text = polisher.polish(text, model=self.config.ollama_model, base_url=self.config.ollama_url)
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
        self._timer_stop = threading.Event()
        threading.Thread(
            target=self._meeting_timer,
            args=(time.monotonic(), self._timer_stop),
            daemon=True,
        ).start()
        rumps.notification("Panda Voice", "Meeting started", "Recording… click Stop Meeting when done.")

    def _meeting_timer(self, start: float, stop: threading.Event):
        while not stop.is_set():
            elapsed = int(time.monotonic() - start)
            m, s = divmod(elapsed, 60)
            h, m = divmod(m, 60)
            self.title = f"🔴 REC {h:02d}:{m:02d}:{s:02d}" if h else f"🔴 REC {m:02d}:{s:02d}"
            stop.wait(1.0)

    def _stop_meeting(self, _):
        if self.state != AppState.MEETING or self._meeting is None:
            return
        if self._timer_stop:
            self._timer_stop.set()
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
            self._refresh_last_notes()
            rumps.notification("Panda Voice", "Meeting notes saved", path)
        except Exception as e:
            logger.error("Meeting finalization error: %s", e)
            raw = str(meeting.transcript_path) if meeting.transcript_path else "unknown"
            rumps.notification("Panda Voice", "Error generating notes", f"Raw transcript saved to {raw}")
        finally:
            self._set_state(AppState.IDLE)
            self._menu_start_meeting.set_callback(self._start_meeting)

    # ── Last Notes ────────────────────────────────────────────────────────────

    def _refresh_last_notes(self):
        folder = Path(self.config.output_dir)
        try:
            self._menu_last_notes.clear()
        except AttributeError:
            pass  # NSMenu not yet initialised on first call
        if folder.exists():
            files = sorted(folder.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        else:
            files = []
        if files:
            for f in files:
                item = rumps.MenuItem(f.stem, callback=lambda _, p=f: subprocess.run(["open", str(p)]))
                self._menu_last_notes.add(item)
        else:
            placeholder = rumps.MenuItem("No notes yet")
            placeholder.set_callback(None)
            self._menu_last_notes.add(placeholder)

    def _open_notes_folder(self, _):
        folder = Path(self.config.output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(folder)])

    # ── Settings ──────────────────────────────────────────────────────────────

    _MODELS = ["tiny", "base", "small", "medium", "turbo"]
    _BACKENDS = ["minimax", "ollama", "claude", "none"]

    def _build_settings_menu(self) -> rumps.MenuItem:
        # Whisper model submenu
        self._model_items: dict[str, rumps.MenuItem] = {}
        menu_model = rumps.MenuItem("Whisper Model")
        for name in self._MODELS:
            item = rumps.MenuItem(name, callback=self._set_model)
            item.state = 1 if name == self.config.model else 0
            self._model_items[name] = item
            menu_model.add(item)

        # Polish text toggle
        self._menu_polish_toggle = rumps.MenuItem("", callback=self._toggle_polish)
        self._update_polish_label()

        # Polish backend submenu
        self._backend_items: dict[str, rumps.MenuItem] = {}
        menu_backend = rumps.MenuItem("Polish Backend")
        for name in self._BACKENDS:
            item = rumps.MenuItem(name, callback=self._set_backend)
            item.state = 1 if name == self.config.polish_backend else 0
            self._backend_items[name] = item
            menu_backend.add(item)

        # API key dialog
        menu_api_key = rumps.MenuItem("Set API Key…", callback=self._set_api_key)

        # Launch at login toggle
        self._menu_login = rumps.MenuItem("Launch at Login", callback=self._toggle_login)
        self._menu_login.state = 1 if self._has_login_item() else 0

        settings = rumps.MenuItem("Settings")
        settings.add(menu_model)
        settings.add(None)
        settings.add(self._menu_polish_toggle)
        settings.add(menu_backend)
        settings.add(None)
        settings.add(menu_api_key)
        settings.add(None)
        settings.add(self._menu_login)
        return settings

    def _update_polish_label(self):
        state = "ON" if self.config.polish_text else "OFF"
        self._menu_polish_toggle.title = f"Polish Text: {state}"

    def _set_model(self, sender):
        for name, item in self._model_items.items():
            item.state = 1 if name == sender.title else 0
        self.config.model = sender.title
        self.config.save()

    def _toggle_polish(self, _):
        self.config.polish_text = not self.config.polish_text
        self.config.save()
        self._update_polish_label()

    def _set_backend(self, sender):
        for name, item in self._backend_items.items():
            item.state = 1 if name == sender.title else 0
        self.config.polish_backend = sender.title
        self.config.save()

    def _set_api_key(self, _):
        win = rumps.Window(
            message="Enter your Anthropic API key (sk-ant-…).\nLeave blank to clear.",
            title="Panda Voice — API Key",
            default_text=self.config.anthropic_api_key or "",
            ok="Save",
            cancel="Cancel",
            dimensions=(400, 24),
        )
        resp = win.run()
        if resp.clicked:
            self.config.anthropic_api_key = resp.text.strip()
            self.config.save()
            status = "saved" if self.config.anthropic_api_key else "cleared"
            rumps.notification("Panda Voice", "API Key", f"Anthropic API key {status}.")

    def _app_bundle_path(self) -> str:
        return str(Path(__file__).parent.parent / "Panda Voice.app")

    def _has_login_item(self) -> bool:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to return (name of login items) contains "Panda Voice"'],
            capture_output=True, text=True,
        )
        return result.stdout.strip() == "true"

    def _toggle_login(self, _):
        if self._has_login_item():
            subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to delete login item "Panda Voice"'],
                capture_output=True,
            )
            self._menu_login.state = 0
        else:
            app_path = self._app_bundle_path()
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "System Events" to make login item at end'
                 f' with properties {{path:"{app_path}", hidden:false}}'],
                capture_output=True,
            )
            self._menu_login.state = 1
