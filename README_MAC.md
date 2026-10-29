# VanishCam on macOS (Intel + Apple Silicon)

Native macOS support for VanishCam. Works on both Apple Silicon (M1/M2/M3/M4) and
Intel Macs. The Python code is already cross-platform; this adds the launcher and
build scripts the Windows side has.

## Quick start

```bash
# 1. Install prerequisites
brew install python@3.12
brew install --cask obs            # ships OBS Virtual Camera

# 2. Grant Terminal access to the camera
#    System Settings → Privacy & Security → Camera → enable your terminal
#    (Terminal, iTerm2, Warp, VS Code, whichever you'll run the launcher from)

# 3. Open OBS once and let it install the virtual camera driver
#    Tools → Start Virtual Camera (then stop it; VanishCam will drive it instead)

# 4. Run
./START_LOCAL.sh
```

The first run creates a `.venv-local/` and installs the Python dependencies
(mediapipe, opencv, numpy, pyvirtualcam, pygame). Subsequent runs skip that step.

## Launchers

| Script | Purpose |
|---|---|
| `START_LOCAL.sh` | Default. Opens preview and auto-attaches to OBS Virtual Camera if available. |
| `START_VIRTUAL.sh` | Fails if no virtual camera backend is available. Use for Zoom/Teams/Meet routing. |
| `START_OBS.sh` | Disables virtual output; use with OBS Window Capture of "Webcam - Preview". |

Both scripts accept all the Python flags, e.g.:

```bash
./START_LOCAL.sh --mode naruto --camera 1 --width 1280 --height 720 --fps 30
./START_LOCAL.sh --gesture-debug
```

## Using the virtual camera from Zoom / Teams / Meet

1. Start VanishCam with `./START_VIRTUAL.sh`.
2. In the client app, pick **OBS Virtual Camera** as the webcam.
3. If the app does not show the virtual camera:
   - **Zoom** (macOS): Preferences → Zoom → tick *Allow use of plug-ins by third-party conference services*. Zoom ≥ 5.9 handles OBS Virtual Camera without hacks.
   - **Teams desktop**: works out of the box on recent builds; log out and back in if it does not appear.
   - **Chrome (Meet, Jitsi, Discord web)**: `chrome://settings/content/camera` → confirm OBS Virtual Camera is listed and allowed.
4. If OBS Virtual Camera does not show at all, open OBS once and run *Tools → Start Virtual Camera* so the system registers the driver. Then stop it in OBS before launching VanishCam (only one process can drive the output).

### App compatibility on macOS

OBS Virtual Camera registers itself as a **DAL (Device Abstraction Layer) plug-in**, the old macOS camera API. Apps built with the hardened runtime need the `com.apple.security.cs.disable-library-validation` entitlement to load third-party DAL plug-ins. The ones below have been checked against this fork.

| App | Status | Notes |
|---|---|---|
| **Zoom** (≥ 5.9) | Works | Enable *Allow use of plug-ins by third-party conference services* in Preferences the first time. |
| **Microsoft Teams** desktop | Works | Pick *OBS Virtual Camera* in the camera selector. Restart Teams if it does not appear after installing OBS. |
| **Google Meet** (Chrome / Safari / Edge) | Works | Any WebRTC browser picks the device up natively. |
| **Discord** desktop | Works | Settings → Voice & Video → Camera. |
| **OBS Studio** itself | Works | Add a *Video Capture Device* source. Do not route it back into its own virtual camera at the same time. |
| **QuickTime** | Works | File → New Movie Recording → arrow next to the record button. |
| **WhatsApp Desktop** | **Does not work** | Electron app with hardened runtime, no DAL entitlement — shows a black feed. **Use [WhatsApp Web](https://web.whatsapp.com) in a browser instead**; video calls work there. |
| **FaceTime** | **Does not work** | Apple's own app refuses non-Apple DAL plug-ins. No workaround. |
| **Messages** | **Does not work** | Same reason as FaceTime. |
| **Mail** (video attachments) | **Does not work** | Hardened runtime, no entitlement. |
| **Signal Desktop** | Flaky | Electron app, DAL load depends on the build; works on some versions. If broken, use Signal in a browser. |

Rule of thumb: if the app is **Electron / hardened runtime without camera entitlement**, OBS Virtual Camera is invisible to it and you get a black feed. For those, your options are:

1. **Browser version** of the service (WhatsApp Web, Signal Web). WebRTC in Chrome / Safari / Edge sees DAL devices without extra setup.
2. **Paid alternative**: [Camo Studio](https://reincubator.com/camo) registers its virtual camera through Core Media IO instead of DAL, so the hardened-runtime apps accept it. Overkill unless you need WhatsApp Desktop specifically.
3. **Re-signing the receiving app** to add the DAL entitlement — technically possible, breaks the vendor's signature and future updates, not recommended.

## Native build (optional)

Produce a `.app` bundle you can drop in `/Applications`:

```bash
./BUILD_MAC.sh
open dist/VanishCam.app
```

The script auto-detects the current architecture. Run it on an Apple Silicon Mac
to get an arm64 build; run it on an Intel Mac to get an x86_64 build. There is no
universal2 wheel for every dependency, so a universal binary is not provided; ship
two architecture-specific `.app`s instead.

Build output: `dist/VanishCam.app`. First launch Finder will show the Gatekeeper
dialog ("downloaded from internet / unknown developer"). Either right-click →
Open the first time, or run `xattr -dr com.apple.quarantine dist/VanishCam.app`
to clear the quarantine flag locally.

### Icon

The repo ships a Windows `.ico`. To get a crisp icon in Finder, convert it to
`.icns` once:

```bash
mkdir -p assets/vanish_icon.iconset
sips -z 1024 1024 assets/vanish_icon.ico --out assets/vanish_icon.iconset/icon_512x512@2x.png
iconutil -c icns -o assets/vanish_icon.icns assets/vanish_icon.iconset
rm -rf assets/vanish_icon.iconset
```

The build script picks `.icns` automatically if present.

## Troubleshooting

- **`AVFoundation` camera open fails**: terminal lacks camera permission. Grant it
  in `System Settings → Privacy & Security → Camera`, then quit and relaunch the
  terminal (the capability is granted at process start).
- **`pyvirtualcam` says no backend**: OBS not installed, or OBS Virtual Camera
  driver not registered. `brew install --cask obs`, launch OBS, use *Tools → Start
  Virtual Camera* once, close OBS, retry.
- **mediapipe install fails on Python 3.13**: downgrade to Python 3.11 or 3.12.
  mediapipe wheels do not cover 3.13 yet on macOS at the time of writing.
  `brew install python@3.12 && rm -rf .venv-local && ./START_LOCAL.sh`.
- **Rosetta on Apple Silicon**: not needed. All dependencies have native arm64
  wheels. If you accidentally created the venv under Rosetta, delete `.venv-local`
  and relaunch so a native venv is created.
- **Zoom shows a black feed**: pyvirtualcam is sending BGR, OBS converts it to
  the format the receiver expects. If the feed is black, confirm no other process
  is holding the OBS Virtual Camera (`lsof | grep -i obsdalplugin`).
