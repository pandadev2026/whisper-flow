from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


STATE_ICONS = {
    AppState.IDLE: "🎤",
    AppState.RECORDING: "🔴",
    AppState.TRANSCRIBING: "⏳",
}
