import threading
import pyaudio

RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024


class Recorder:
    def __init__(self):
        self._audio = pyaudio.PyAudio()
        self._chunks = []
        self._recording = False
        self._lock = threading.Lock()
        self._thread = None

    def start(self):
        with self._lock:
            if self._recording:
                return
            self._chunks = []
            self._recording = True
        self._thread = threading.Thread(target=self._capture, daemon=True)
        self._thread.start()

    def stop(self) -> list:
        with self._lock:
            self._recording = False
        if self._thread and self._thread.ident is not None:
            self._thread.join(timeout=2.0)
        return list(self._chunks)

    def _capture(self):
        stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        try:
            while self._recording:
                data = stream.read(CHUNK, exception_on_overflow=False)
                self._chunks.append(data)
        finally:
            stream.stop_stream()
            stream.close()
