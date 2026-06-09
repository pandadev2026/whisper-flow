import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
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
