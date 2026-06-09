import logging
import threading
import time

import whisperflow.transcriber as ts
from panda_voice.recorder import Recorder

logger = logging.getLogger(__name__)

CHUNK_SECONDS = 30


class MeetingRecorder:
    def __init__(self, model, config):
        self._model = model
        self._config = config
        self._recorder = Recorder()
        self._segments: list[str] = []
        self._running = False
        self._thread = None

    def start(self):
        self._segments = []
        self._running = True
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
                self._segments.append(text)
        return list(self._segments)

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
                        self._segments.append(text)
                        logger.info("Meeting segment %d: %s…", len(self._segments), text[:60])

    def _transcribe(self, chunks: list) -> str:
        try:
            lang = None if self._config.language == "auto" else self._config.language
            result = ts.transcribe_pcm_chunks(self._model, chunks, lang=lang)
            return result.get("text", "").strip()
        except Exception as e:
            logger.warning("Meeting transcription error: %s", e)
            return ""
