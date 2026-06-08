import time
import pyperclip
from pynput.keyboard import Key, Controller

_keyboard = Controller()


def paste_text(text: str, restore_clipboard: bool = True):
    if not text or not text.strip():
        return

    original = ""
    if restore_clipboard:
        try:
            original = pyperclip.paste()
        except Exception:
            pass

    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        with _keyboard.pressed(Key.cmd):
            _keyboard.press("v")
            _keyboard.release("v")
        time.sleep(0.1)
    finally:
        if restore_clipboard and original:
            time.sleep(0.05)
            pyperclip.copy(original)
