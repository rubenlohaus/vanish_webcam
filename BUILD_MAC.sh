#!/usr/bin/env bash
# PyInstaller build for macOS. Produces a native .app for the current architecture
# (Intel x86_64 or Apple Silicon arm64). Run on both archs to ship a universal pair.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv-build"
VENV_PY="$VENV_DIR/bin/python"
ARCH="$(uname -m)"   # arm64 (Apple Silicon) or x86_64 (Intel)

if [[ ! -x "$VENV_PY" ]]; then
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then SYS_PY="$candidate"; break; fi
  done
  [[ -z "${SYS_PY:-}" ]] && { echo "Python 3 non trovato (prova: brew install python@3.12)"; exit 1; }
  echo "[build] Creo venv con $SYS_PY..."
  "$SYS_PY" -m venv "$VENV_DIR"
fi

if ! "$VENV_PY" -c "import PyInstaller, cv2, mediapipe, numpy, pyvirtualcam, pygame" >/dev/null 2>&1; then
  echo "[build] Installo le dipendenze di build..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt "pyinstaller>=6,<7"
fi

if [[ ! -f "models/gesture_recognizer.task" || ! -f "models/selfie_segmenter_landscape.tflite" ]]; then
  echo "[build] Scarico i modelli MediaPipe..."
  "$VENV_PY" -c "from vanish_cam import download_models; download_models()"
fi

echo "[build] PyInstaller target_arch=$ARCH"
"$VENV_PY" -m PyInstaller --noconfirm --distpath dist --workpath build VanishCam_mac.spec

APP="dist/VanishCam.app"
[[ -d "$APP" ]] || { echo "[build] .app non generata"; exit 1; }

echo "[build] Self-test..."
"$APP/Contents/MacOS/VanishCam" --self-test

echo
echo "Pronto: $APP  (arch: $ARCH)"
echo "Per correrla:  open $APP"
echo "Per log/output: $APP/Contents/MacOS/VanishCam"
