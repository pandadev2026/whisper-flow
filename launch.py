import logging
import sys
from pathlib import Path

_log_file = Path.home() / ".panda-voice" / "panda-voice.log"
_log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_log_file),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)


def main():
    from panda_voice.config import Config
    config = Config()

    print("🎤 Panda Voice starting...")

    print(f"   Loading Whisper model ({config.model})...")
    import whisperflow.transcriber as ts
    model = ts.get_model(config.model)
    print("   Whisper ready ✓")

    print("   Starting menu bar app...")
    print("   Hold left Option to dictate into any app.\n")

    from panda_voice.app import PandaVoiceApp
    PandaVoiceApp(model).run()


if __name__ == "__main__":
    main()
