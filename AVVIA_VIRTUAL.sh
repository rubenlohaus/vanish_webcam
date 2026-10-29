#!/usr/bin/env bash
# Launch VanishCam requiring the virtual camera output (OBS Virtual Camera on macOS,
# v4l2loopback on Linux). Fails if no backend is available.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/AVVIA_LOCALE.sh" --virtual-camera "$@"
