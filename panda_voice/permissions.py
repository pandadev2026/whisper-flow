import logging
import subprocess

logger = logging.getLogger(__name__)

_URL_ACCESSIBILITY = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
_URL_MICROPHONE = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"

# AVAuthorizationStatus values
_AV_NOT_DETERMINED = 0
_AV_DENIED = 2
_AV_AUTHORIZED = 3


def accessibility_granted() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception as e:
        logger.warning("Could not check Accessibility permission: %s", e)
        return True


def microphone_status() -> int:
    """Returns AVAuthorizationStatus int: 0=notDetermined, 1=restricted, 2=denied, 3=authorized."""
    try:
        import objc
        objc.loadBundle(
            "AVFoundation", globals(),
            bundle_path="/System/Library/Frameworks/AVFoundation.framework",
        )
        AVCaptureDevice = objc.lookUpClass("AVCaptureDevice")
        return int(AVCaptureDevice.authorizationStatusForMediaType_("soun"))
    except Exception as e:
        logger.warning("Could not check Microphone permission: %s", e)
        return _AV_AUTHORIZED


def request_microphone() -> bool:
    """Trigger the system microphone permission prompt and return whether granted."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16, channels=1, rate=16000,
            input=True, frames_per_buffer=512,
        )
        stream.read(512, exception_on_overflow=False)
        stream.close()
        pa.terminate()
        return True
    except Exception:
        return False


def open_settings(url: str):
    subprocess.run(["open", url], capture_output=True)


def missing() -> list[dict]:
    """
    Returns a list of dicts for each missing permission:
      {"name": str, "message": str, "url": str, "can_prompt": bool}
    """
    issues = []

    if not accessibility_granted():
        issues.append({
            "name": "Accessibility",
            "message": (
                "Panda Voice needs Accessibility permission to detect the Option key.\n\n"
                "Open System Settings → Privacy & Security → Accessibility,\n"
                "then enable Panda Voice and restart the app."
            ),
            "url": _URL_ACCESSIBILITY,
            "can_prompt": False,
        })

    mic = microphone_status()
    if mic == _AV_NOT_DETERMINED:
        issues.append({
            "name": "Microphone",
            "message": (
                "Panda Voice needs Microphone access to record audio.\n\n"
                "Click Request Access — macOS will ask for permission."
            ),
            "url": _URL_MICROPHONE,
            "can_prompt": True,
        })
    elif mic == _AV_DENIED:
        issues.append({
            "name": "Microphone",
            "message": (
                "Microphone access was previously denied.\n\n"
                "Open System Settings → Privacy & Security → Microphone\n"
                "and enable Panda Voice."
            ),
            "url": _URL_MICROPHONE,
            "can_prompt": False,
        })

    return issues
