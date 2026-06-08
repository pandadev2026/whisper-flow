import threading
from pynput import keyboard


class HotkeyManager:
    def __init__(self, on_activate, on_deactivate):
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._pressed = set()
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

    def _is_hotkey(self, keys):
        has_alt = any(
            k in keys
            for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
        )
        has_space = keyboard.Key.space in keys
        return has_alt and has_space

    def _on_press(self, key):
        self._pressed.add(key)
        if not self._active and self._is_hotkey(self._pressed):
            self._active = True
            threading.Thread(target=self._on_activate, daemon=True).start()

    def _on_release(self, key):
        if self._active and self._is_hotkey(self._pressed):
            self._active = False
            threading.Thread(target=self._on_deactivate, daemon=True).start()
        self._pressed.discard(key)
