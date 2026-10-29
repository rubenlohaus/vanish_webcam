#!/usr/bin/env bash
# VanishCam launcher for macOS (Intel + Apple Silicon) and Linux.
# Creates a local virtualenv, installs the requirements once, and starts the app.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv-local"
VENV_PY="$VENV_DIR/bin/python"

pick_python() {
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if [[ ! -x "$VENV_PY" ]]; then
  SYS_PY="$(pick_python)" || {
    echo "[VanishCam] Python 3 non trovato. Installa Python 3.11 o 3.12."
    echo "            macOS:  brew install python@3.12"
    echo "            oppure: https://www.python.org/downloads/macos/"
    exit 1
  }
  echo "[VanishCam] Creo l'ambiente Python locale con $SYS_PY..."
  "$SYS_PY" -m venv "$VENV_DIR"
fi

if ! "$VENV_PY" -c "import cv2, mediapipe, numpy, pyvirtualcam, pygame" >/dev/null 2>&1; then
  echo "[VanishCam] Installo le dipendenze (serve internet solo la prima volta)..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r requirements.txt
fi

echo "[VanishCam] Avvio la webcam..."
exec "$VENV_PY" vanish_cam.py "$@"
