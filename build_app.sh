#!/bin/bash
# build_app.sh — packages Panda Voice as a self-contained .app bundle
# Usage: ./build_app.sh
# The resulting "Panda Voice.app" can be moved to /Applications/ and run standalone.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SCRIPT_DIR/Panda Voice.app"
RESOURCES="$APP/Contents/Resources"
FRAMEWORKS="$APP/Contents/Frameworks"
MACOS="$APP/Contents/MacOS"

echo "╔══════════════════════════════════════╗"
echo "║   Building Panda Voice.app           ║"
echo "╚══════════════════════════════════════╝"

# ── 1. Directory structure ────────────────────────────────────────────────────
echo ""
echo "▶ Setting up bundle directories..."
mkdir -p "$RESOURCES" "$FRAMEWORKS" "$MACOS"

# ── 2. Copy Python source ────────────────────────────────────────────────────
echo "▶ Copying source files..."
cp "$SCRIPT_DIR/launch.py" "$RESOURCES/"
rm -rf "$RESOURCES/panda_voice" "$RESOURCES/whisperflow"
cp -r "$SCRIPT_DIR/panda_voice"  "$RESOURCES/"
cp -r "$SCRIPT_DIR/whisperflow"  "$RESOURCES/"
# Remove caches that embed absolute paths
find "$RESOURCES" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── 3. Embedded Python venv ──────────────────────────────────────────────────
echo "▶ Creating embedded venv (this takes a few minutes)..."
PYTHON=$(which python3.12 2>/dev/null || which python3)
"$PYTHON" -m venv --copies "$RESOURCES/.venv"
"$RESOURCES/.venv/bin/pip" install --upgrade pip --quiet

echo "▶ Installing runtime dependencies (torch is ~500 MB, please wait)..."
"$RESOURCES/.venv/bin/pip" install \
    -r "$SCRIPT_DIR/requirements-app.txt" \
    --quiet --no-warn-script-location

# ── 4. Bundle PortAudio ──────────────────────────────────────────────────────
echo "▶ Bundling PortAudio..."
PORTAUDIO_SRC=$(find /opt/homebrew/opt/portaudio/lib /opt/homebrew/lib \
    -name "libportaudio.2.dylib" 2>/dev/null | head -1)
if [ -z "$PORTAUDIO_SRC" ]; then
    echo "ERROR: libportaudio.2.dylib not found. Run: brew install portaudio"
    exit 1
fi

# Copy dylib next to the PyAudio .so so @loader_path resolves correctly
PYAUDIO_DIR=$(find "$RESOURCES/.venv" -name "_portaudio*.so" -exec dirname {} \; | head -1)
if [ -z "$PYAUDIO_DIR" ]; then
    echo "ERROR: _portaudio*.so not found in venv"
    exit 1
fi

PORTAUDIO_DEST="$PYAUDIO_DIR/libportaudio.2.dylib"
cp "$PORTAUDIO_SRC" "$PORTAUDIO_DEST"
chmod 644 "$PORTAUDIO_DEST"

# Rewrite PyAudio's rpath to use the bundled copy
PYAUDIO_SO=$(find "$PYAUDIO_DIR" -name "_portaudio*.so")
OLD_RPATH=$(otool -L "$PYAUDIO_SO" | awk '/libportaudio/{print $1}')
if [ -n "$OLD_RPATH" ]; then
    install_name_tool -change "$OLD_RPATH" \
        "@loader_path/libportaudio.2.dylib" "$PYAUDIO_SO"
    echo "  Rewrote rpath: $OLD_RPATH → @loader_path/libportaudio.2.dylib"
fi

# ── 5. Bundle Python.framework dylib ─────────────────────────────────────────
echo "▶ Bundling Python.framework..."
# Find the Cellar path baked into the venv Python binary
OLD_PY_DYLIB=$(otool -L "$RESOURCES/.venv/bin/python" | awk '/Cellar.*Python/{print $1}')
if [ -z "$OLD_PY_DYLIB" ]; then
    echo "ERROR: could not detect Homebrew Python dylib path in venv"
    exit 1
fi

# Copy the dylib into Contents/Frameworks/ (preserving framework subdirectory structure)
PY_FW_DEST="$FRAMEWORKS/Python.framework/Versions/3.12"
mkdir -p "$PY_FW_DEST"
cp "$OLD_PY_DYLIB" "$PY_FW_DEST/Python"
chmod 755 "$PY_FW_DEST/Python"

# Rewrite the reference in all three Python binaries
NEW_PY_REF="@executable_path/../../../Frameworks/Python.framework/Versions/3.12/Python"
for PY_BIN in "$RESOURCES/.venv/bin/python" "$RESOURCES/.venv/bin/python3" "$RESOURCES/.venv/bin/python3.12"; do
    if [ -f "$PY_BIN" ]; then
        install_name_tool -change "$OLD_PY_DYLIB" "$NEW_PY_REF" "$PY_BIN"
    fi
done
echo "  Rewrote Python.framework ref: $(basename "$OLD_PY_DYLIB" | cut -c1-60)... → @executable_path/../../../Frameworks/..."

# ── 7. Compile Swift launcher ────────────────────────────────────────────────
echo "▶ Compiling Swift launcher..."
swiftc -O -strict-concurrency=minimal \
    "$SCRIPT_DIR/swift_launcher/main.swift" \
    -o "$MACOS/PandaVoice"

# ── 8. Verify ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Verifying bundle..."
PYTHON_BIN="$RESOURCES/.venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    echo "ERROR: Python binary not found at $PYTHON_BIN"
    exit 1
fi

# Quick import check
"$PYTHON_BIN" -c "
import sys, os
sys.path.insert(0, '$RESOURCES')
from panda_voice.config import Config
from panda_voice.hotkey import HotkeyManager
import whisperflow.transcriber
import rumps, pyaudio, pynput
print('  All imports OK')
"

BUNDLE_SIZE=$(du -sh "$APP" 2>/dev/null | cut -f1)
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Build complete ✓                   ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Bundle : $APP"
echo "  Size   : $BUNDLE_SIZE"
echo ""
echo "  Next steps:"
echo "  1. cp -r \"Panda Voice.app\" /Applications/"
echo "  2. Open /Applications/Panda Voice.app"
echo "  3. Grant Accessibility permission when prompted"
