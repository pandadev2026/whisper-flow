import logging
import os
import threading
from pynput import keyboard
from pynput.keyboard import Key

logger = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self, on_activate, on_deactivate):
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._active = False
        self._listener = None

    def start(self):
        fifo_path = os.environ.get("PANDA_HOTKEY_FIFO")
        if os.environ.get("PANDA_SWIFT_LAUNCHER") == "1" and fifo_path:
            logger.info("Swift launcher detected — reading hotkey events from FIFO: %s", fifo_path)
            threading.Thread(target=self._fifo_loop, args=(fifo_path,), daemon=True).start()
        else:
            logger.info("No Swift launcher — using pynput for hotkey detection")
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _fifo_loop(self, fifo_path: str):
        try:
            with open(fifo_path, "r") as f:
                for line in f:
                    cmd = line.strip()
                    if cmd == "D" and not self._active:
                        self._active = True
                        threading.Thread(target=self._on_activate, daemon=True).start()
                    elif cmd == "U" and self._active:
                        self._active = False
                        threading.Thread(target=self._on_deactivate, daemon=True).start()
        except OSError as e:
            logger.error("FIFO read error (Swift launcher exited?): %s", e)

    def _on_press(self, key):
        if not self._active and key == Key.alt_l:
            self._active = True
            threading.Thread(target=self._on_activate, daemon=True).start()

    def _on_release(self, key):
        if self._active and key == Key.alt_l:
            self._active = False
            threading.Thread(target=self._on_deactivate, daemon=True).start()
