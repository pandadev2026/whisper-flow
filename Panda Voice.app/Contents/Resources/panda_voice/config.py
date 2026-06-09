import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".panda-voice"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "hotkey": "<alt_l>",
    "model": "base",
    "language": "auto",
    "output_dir": str(Path.home() / "Documents" / "MeetingNotes"),
    "anthropic_api_key": "",
    "restore_clipboard": True,
    "polish_text": False,
    "polish_backend": "minimax",  # minimax | claude | ollama | none
    "ollama_model": "qwen2.5:7b",
    "ollama_url": "http://localhost:11434",
    "minimax_api_key": "",
    "minimax_group_id": "",
    "minimax_model": "MiniMax-Text-01",
    "minimax_url": "https://api.minimax.chat/v1",
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)
        CONFIG_FILE.chmod(0o600)

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self._data[key] = value
