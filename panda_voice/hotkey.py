import threading
from pynput import keyboard
from pynput.keyboard import Key


class HotkeyManager:
    def __init__(self, on_activate, on_deactivate):
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._active = False
        self._listener = None

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_press(self, key):
        if not self._active and key == Key.alt_l:
            self._active = True
            threading.Thread(target=self._on_activate, daemon=True).start()

    def _on_release(self, key):
        if self._active and key == Key.alt_l:
            self._active = False
            threading.Thread(target=self._on_deactivate, daemon=True).start()
