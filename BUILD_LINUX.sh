#!/usr/bin/env bash
# PyInstaller build for Linux. Produces a single-folder VanishCam binary under
# dist/VanishCam/ for the host architecture (x86_64 or aarch64).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv-build"
VENV_PY="$VENV_DIR/bin/python"
ARCH="$(uname -m)"

if [[ ! -x "$VENV_PY" ]]; then
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then SYS_PY="$candidate"; break; fi
  done
  [[ -z "${SYS_PY:-}" ]] && {
    echo "Python 3 not found. Install python3.11 or 3.12 via your package manager."
    exit 1
  }
  echo "[build] Creating venv with $SYS_PY..."
  "$SYS_PY" -m venv "$VENV_DIR"
fi

if ! "$VENV_PY" -c "import PyInstaller, cv2, mediapipe, numpy, pyvirtualcam, pygame" >/dev/null 2>&1; then
  echo "[build] Installing build dependencies..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt "pyinstaller>=6,<7"
fi

if [[ ! -f "models/gesture_recognizer.task" || ! -f "models/selfie_segmenter_landscape.tflite" ]]; then
  echo "[build] Downloading MediaPipe models..."
  "$VENV_PY" -c "from vanish_cam import download_models; download_models('goku')"
fi

echo "[build] PyInstaller target_arch=$ARCH"
"$VENV_PY" -m PyInstaller --noconfirm --distpath dist --workpath build VanishCam_linux.spec

BIN="dist/VanishCam/VanishCam"
[[ -x "$BIN" ]] || { echo "[build] binary was not generated"; exit 1; }

echo "[build] Self-test..."
"$BIN" --self-test

echo
echo "Ready: $BIN  (arch: $ARCH)"
echo "To run:       $BIN --mode goku"
echo "Virtual cam:  $BIN --mode goku --virtual-backend v4l2loopback --virtual-device /dev/video10"
