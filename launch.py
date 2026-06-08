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

    print("   Loading Whisper model (base)...")
    import whisperflow.transcriber as ts
    model = ts.get_model("base")
    print("   Whisper ready ✓")

    if config.polish_text and config.polish_backend == "ollama":
        print(f"   Warming up Ollama ({config.ollama_model})...")
        from panda_voice import polisher
        polisher.warm_up(model=config.ollama_model, base_url=config.ollama_url)
        print("   Ollama ready ✓")

    print("   Starting menu bar app...")
    print("   Hold Option+Space to dictate into any app.\n")

    from panda_voice.app import PandaVoiceApp
    PandaVoiceApp(model).run()


if __name__ == "__main__":
    main()
