"""Preload the Instant Transmission MP3 and play forward or reversed.

The buffer is trimmed so the loudest sample lands at the vanish moment for forward
playback and at the reappear moment for the reversed playback — same mechanism
the HTML preview uses with Web Audio.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np


SOUND_PATH = Path(__file__).resolve().parent / "assets" / "teleport.mp3"


def _trim_to_target(samples: np.ndarray, sample_rate: int, target_s: float) -> np.ndarray:
    """Return samples starting at ``peak_time - target_s`` so the peak amplitude
    lands ``target_s`` seconds after playback begins. If the peak is earlier than
    the target, play from the start (sound will trigger slightly early)."""
    if samples.size == 0:
        return samples
    amplitude = np.abs(samples)
    if amplitude.ndim > 1:
        amplitude = amplitude.max(axis=1)
    peak_idx = int(np.argmax(amplitude))
    peak_s = peak_idx / sample_rate
    offset_s = max(0.0, peak_s - target_s)
    start = int(offset_s * sample_rate)
    return samples[start:]


class TeleportSound:
    """Pygame-backed teleport sound with pre-aligned forward and reversed buffers."""

    def __init__(self, cfg: dict, path: Path = SOUND_PATH, device: str | None = None) -> None:
        if not path.is_file():
            raise RuntimeError(f"Teleport audio not found: {path}")
        self.path = path
        self.cfg = cfg
        self.device = device or None

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        self.ffplay = None
        self.ffplay_process = None
        self.mixer = None
        self.owns_mixer = False
        self.forward_sound = None
        self.reverse_sound = None

        try:
            from pygame import mixer, sndarray
        except ImportError:
            self._init_ffplay_fallback()
            return

        self.mixer = mixer
        self.owns_mixer = mixer.get_init() is None
        try:
            if self.owns_mixer:
                init_kwargs = dict(frequency=44100, size=-16, channels=2, buffer=256)
                if self.device:
                    init_kwargs["devicename"] = self.device
                mixer.init(**init_kwargs)
            raw = mixer.Sound(str(path))
            samples = sndarray.array(raw)
            del raw  # we only need the samples now
            freq = mixer.get_init()[0] if mixer.get_init() else 44100
            self._build_sounds(samples, freq, sndarray)
        except Exception as error:
            if self.owns_mixer:
                mixer.quit()
            # Fall back to ffplay before giving up entirely.
            self.mixer = None
            self.owns_mixer = False
            self._init_ffplay_fallback(reason=str(error))

    # -- initialization helpers --

    def _build_sounds(self, samples: np.ndarray, freq: int, sndarray) -> None:
        forward_target = (self.cfg["charge_ms"] + self.cfg["pop_ms"] * 0.5) / 1000.0
        reverse_target = (self.cfg["linger_ms"] + self.cfg["vanish_ms"]) / 1000.0

        forward_trimmed = _trim_to_target(samples, freq, forward_target)
        reversed_full = np.ascontiguousarray(samples[::-1])
        reverse_trimmed = _trim_to_target(reversed_full, freq, reverse_target)

        self.forward_sound = sndarray.make_sound(np.ascontiguousarray(forward_trimmed))
        self.reverse_sound = sndarray.make_sound(np.ascontiguousarray(reverse_trimmed))

    def _init_ffplay_fallback(self, reason: str | None = None) -> None:
        self.ffplay = shutil.which("ffplay")
        if self.ffplay is None:
            hint = f" ({reason})" if reason else ""
            raise RuntimeError(
                f"To play teleport.mp3 install pygame or ffplay{hint}."
            )

    # -- playback --

    def play_forward(self) -> None:
        self._play("forward")

    def play_reverse(self) -> None:
        self._play("reverse")

    def _play(self, direction: str) -> None:
        if self.mixer is not None and self.forward_sound is not None:
            sound = self.reverse_sound if direction == "reverse" else self.forward_sound
            sound.stop()
            if sound.play() is None:
                # No free mixer channel; silently drop this cue.
                return
            return
        # ffplay fallback: forward only (reverse would require re-encoding).
        if self.ffplay is None:
            return
        if self.ffplay_process is not None and self.ffplay_process.poll() is None:
            self.ffplay_process.terminate()
        args = [self.ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet"]
        if self.device:
            args += ["-audio_device", self.device]
        if direction == "reverse":
            args += ["-af", "areverse"]
        args += ["-i", str(self.path)]
        try:
            self.ffplay_process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            self.ffplay_process = None

    def close(self) -> None:
        if self.ffplay_process is not None and self.ffplay_process.poll() is None:
            self.ffplay_process.terminate()
        self.ffplay_process = None
        if self.owns_mixer and self.mixer is not None:
            self.mixer.quit()
            self.owns_mixer = False
