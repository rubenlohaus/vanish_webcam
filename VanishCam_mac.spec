"""PyInstaller build for macOS. Produces a VanishCam.app bundle for the current
architecture (arm64 on Apple Silicon, x86_64 on Intel). Mirrors VanishCam.spec but
packages as a .app so Finder, Spotlight and the camera permission prompt work."""

from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs


root = Path(SPECPATH).resolve()
icon_file = root / "assets" / "vanish_icon.icns"
if not icon_file.is_file():
    # Fall back to the .ico; PyInstaller skips the icon silently if it cannot convert.
    icon_file = root / "assets" / "vanish_icon.ico"

resources = [
    (root / "hand_landmarker.task", "."),
    (root / "models" / "gesture_recognizer.task", "models"),
    (root / "models" / "selfie_segmenter_landscape.tflite", "models"),
    (root / "assets" / "substitution_log.png", "assets"),
    (root / "assets" / "vanish.MP3", "assets"),
]
missing = [str(path) for path, _ in resources if not path.is_file()]
if missing:
    raise SystemExit("Build is missing required files:\n" + "\n".join(missing))

a = Analysis(
    [str(root / "vanish_cam.py")],
    pathex=[str(root)],
    binaries=collect_dynamic_libs("mediapipe"),
    datas=[(str(path), destination) for path, destination in resources],
    hiddenimports=["pygame.mixer", "mediapipe.tasks.c"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VanishCam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_file) if icon_file.is_file() else None,
)
app = BUNDLE(
    exe,
    name="VanishCam.app",
    icon=str(icon_file) if icon_file.is_file() else None,
    bundle_identifier="app.vanishcam",
    info_plist={
        "CFBundleName": "VanishCam",
        "CFBundleDisplayName": "VanishCam",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSCameraUsageDescription": "VanishCam processes the webcam locally to apply the vanish effect.",
        "NSMicrophoneUsageDescription": "Not required by VanishCam, declared only for compatibility.",
    },
)
