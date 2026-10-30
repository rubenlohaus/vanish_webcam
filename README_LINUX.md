# VanishCam on Linux

Works on x86_64 and aarch64. The Python code is cross-platform; this adds the
launcher recipes, PyInstaller spec and virtual-camera setup for a Linux host.

## Quick start

```bash
# 1. System dependencies
sudo apt install python3.12 python3.12-venv libgl1 libgles2 ffmpeg   # Debian/Ubuntu
# sudo dnf install python3.12 mesa-libGL mesa-libGLES ffmpeg          # Fedora
# sudo pacman -S python mesa ffmpeg                                   # Arch

# 2. Virtual camera (v4l2loopback) — needed only if you want to pipe the output
#    into Zoom / Meet / OBS as a camera device.
sudo apt install v4l2loopback-dkms v4l2loopback-utils   # Debian/Ubuntu
# sudo dnf install v4l2loopback                          # Fedora (akmod)
# sudo pacman -S v4l2loopback-dkms                       # Arch

# Load the module and create /dev/video10. Repeat on every boot or add to
# /etc/modules-load.d/ for persistence.
sudo modprobe v4l2loopback devices=1 video_nr=10 \
     card_label="VanishCam" exclusive_caps=1

# 3. Make sure your user can read the webcam device.
sudo usermod -a -G video "$USER"   # log out and back in after this.

# 4. Run
./START_LOCAL.sh                                                  # preview only
./START_VIRTUAL.sh --virtual-backend v4l2loopback \
                   --virtual-device /dev/video10                  # feed into v4l2
```

The first run creates `.venv-local/` and installs the Python dependencies
(mediapipe, opencv, numpy, pyvirtualcam, pygame). Subsequent runs skip that step.

## Launchers

| Script | Purpose |
|---|---|
| `START_LOCAL.sh` | Default. Opens the preview and auto-attaches a virtual camera if `--virtual-backend` is passed. |
| `START_VIRTUAL.sh` | Requires a virtual camera backend. Exits with an error if `v4l2loopback` is not loaded. |
| `START_OBS.sh` | Disables virtual output; use with OBS **Window Capture** of `Webcam - Preview`. |

Both scripts accept all the Python flags, e.g.:

```bash
./START_LOCAL.sh --mode goku --camera /dev/video0 --width 1280 --height 720 --fps 30
./START_LOCAL.sh --mode naruto --gesture-debug
```

## Using the virtual camera from Zoom / Meet / Discord / OBS

1. Load the `v4l2loopback` module (see Quick start step 2).
2. Start VanishCam with `./START_VIRTUAL.sh --virtual-backend v4l2loopback --virtual-device /dev/video10`.
3. In the client app, pick **VanishCam** (or `/dev/video10`) as the webcam.
   - **Zoom** desktop (Linux client): Settings → Video → Camera dropdown.
   - **Google Meet / Jitsi / Discord web**: browser camera picker shows it as "VanishCam".
   - **OBS**: Add a *Video Capture Device (V4L2)* source and pick the virtual device.
4. Only one process can write to `/dev/video10` at a time. Close any other app
   that is pushing to it (OBS, another VanishCam instance) before launching.

### Making the Goku teleport sound audible to the other side

v4l2loopback only carries video. The `teleport.mp3` plays on your local
speakers, so the remote side hears nothing. One-time PipeWire setup to mix the
teleport burst into a virtual mic:

```bash
# A silent sink VanishCam will play into
pactl load-module module-null-sink sink_name=vanish_fx \
      sink_properties=device.description=VanishFX

# A virtual mic = your real mic + the monitor of vanish_fx
pactl load-module module-remap-source master=$(pactl get-default-source) \
      source_name=vanish_mic source_properties=device.description=VanishMic
pactl load-module module-loopback source=vanish_fx.monitor sink=vanish_mic
```

Launch VanishCam routing audio to that sink, pass the device flag through:

```bash
PULSE_SINK=vanish_fx ./START_LOCAL.sh --mode goku --audio-device vanish_fx
```

In Zoom / Teams / Meet pick **VanishMic** as the microphone. The teleport
sound mixes in on demand; the real mic keeps working otherwise. For
persistence across reboots, drop the three `pactl load-module` lines into
`~/.config/pipewire/pipewire.conf.d/vanishcam.conf` as declarative modules.

## Native build (optional)

Produce a single-folder binary you can drop into `/opt` or `~/.local/bin`:

```bash
./BUILD_LINUX.sh
dist/VanishCam/VanishCam --mode goku
```

The script auto-detects the current architecture. x86_64 and aarch64 both
work. There is no universal binary — build on the arch you plan to ship to.

Build output: `dist/VanishCam/VanishCam` plus a bundle of shared libraries in
the same folder. Add that folder to `PATH` or symlink the binary.

### Optional .desktop entry

Create `~/.local/share/applications/vanishcam.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=VanishCam
Comment=Disappear from your webcam with Normal, Naruto or Goku effects.
Exec=/path/to/VanishCam --mode goku
Icon=/path/to/vanish_webcam/assets/vanish_icon.ico
Terminal=true
Categories=AudioVideo;Video;
```

Then `update-desktop-database ~/.local/share/applications/`. The `.ico` works
for most launchers (GNOME, KDE); for a crisper icon convert it to a PNG once
with ImageMagick: `convert assets/vanish_icon.ico assets/vanish_icon.png`.

## Troubleshooting

- **`VIDEOIO ERROR: V4L2: ... Can't open device`**: user not in the `video`
  group. `sudo usermod -a -G video "$USER"`, log out and back in. Verify with
  `groups | grep video`.
- **`pyvirtualcam` says no backend**: `v4l2loopback` module not loaded.
  `lsmod | grep v4l2loopback` should list it; if empty, re-run the
  `sudo modprobe v4l2loopback ...` line.
- **Virtual camera does not appear in Zoom**: Zoom caches camera list on launch.
  Close Zoom fully (`pkill zoom`) and reopen.
- **mediapipe install fails on Python 3.13**: downgrade to 3.11 or 3.12.
  Mediapipe wheels do not cover 3.13 on Linux at the time of writing.
- **Wayland crashes on launch**: VanishCam uses OpenCV's `HighGUI` which prefers
  X11. On a Wayland session, OpenCV usually falls back to Xwayland automatically
  if `xwayland` is installed. Install it if the window never appears:
  `sudo apt install xwayland`.
- **No audio on Goku teleport**: pygame needs PulseAudio or Pipewire-pulse. On
  minimal installs: `sudo apt install pulseaudio` (or your distro equivalent).
- **mp3 decode fails** (goku teleport silent): install `libmpg123-0`
  (`sudo apt install libmpg123-0`). SDL_mixer uses it to decode mp3.
