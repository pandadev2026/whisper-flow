import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import whisperflow.transcriber as ts
from panda_voice.recorder import Recorder

logger = logging.getLogger(__name__)

CHUNK_SECONDS = 30
_TRANSCRIPT_DIR = Path.home() / ".panda-voice" / "meetings"


class MeetingRecorder:
    def __init__(self, model, config):
        self._model = model
        self._config = config
        self._recorder = Recorder()
        self._segments: list[str] = []
        self._running = False
        self._thread = None
        self.transcript_path: Path | None = None

    def start(self):
        self._segments = []
        self._running = True
        _TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        self.transcript_path = _TRANSCRIPT_DIR / f"{now.strftime('%Y-%m-%d_%H-%M')}_transcript.txt"
        self.transcript_path.write_text(
            f"Meeting transcript — {now.strftime('%Y-%m-%d %H:%M')}\n\n", encoding="utf-8"
        )
        logger.info("Transcript will be saved to %s", self.transcript_path)
        self._recorder.start()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> list[str]:
        self._running = False
        chunks = self._recorder.stop()
        if self._thread:
            self._thread.join(timeout=5)
        if chunks:
            text = self._transcribe(chunks)
            if text:
                self._append_segment(text)
        return list(self._segments)

    def _append_segment(self, text: str):
        self._segments.append(text)
        if self.transcript_path:
            try:
                with self.transcript_path.open("a", encoding="utf-8") as f:
                    f.write(text + "\n\n")
            except OSError as e:
                logger.warning("Failed to write transcript segment to disk: %s", e)
        logger.info("Meeting segment %d: %s…", len(self._segments), text[:60])

    def _loop(self):
        deadline = time.monotonic() + CHUNK_SECONDS
        while self._running:
            time.sleep(0.5)
            if time.monotonic() >= deadline:
                chunks = self._recorder.stop()
                self._recorder.start()
                deadline = time.monotonic() + CHUNK_SECONDS
                if chunks:
                    text = self._transcribe(chunks)
                    if text:
                        self._append_segment(text)

    def _transcribe(self, chunks: list) -> str:
        try:
            lang = None if self._config.language == "auto" else self._config.language
            result = ts.transcribe_pcm_chunks(self._model, chunks, lang=lang)
            return result.get("text", "").strip()
        except Exception as e:
            logger.warning("Meeting transcription error: %s", e)
            return ""
