#!/usr/bin/env bash
# Launch VanishCam with the virtual-camera output disabled so OBS can capture the
# preview window directly (Window Capture / Display Capture of "Webcam - Preview").
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/START_LOCAL.sh" --no-virtual-camera "$@"
