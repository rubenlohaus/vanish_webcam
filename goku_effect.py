"""Instant Transmission vanish: fingers-to-forehead gesture, ki aura, shūchūsen lines, warp."""

from __future__ import annotations

import dataclasses
import enum
import math
import random

import cv2
import numpy as np


GOKU_DEFAULTS = dict(
    charge_ms=300,
    pop_ms=120,
    vanish_ms=200,
    linger_ms=320,
    gone_ms=700,
    line_density=180,
    line_speed=12.0,
    line_width=2,
    aura=True,
    warp=True,
    auto_reappear=True,
    hold_seconds=1.0,
)

# Ki cyan in BGR (mock palette is CSS rgba(77, 227, 255)).
AURA_COLOR_BGR = (255, 227, 77)


class GokuPhase(enum.IntEnum):
    IDLE = 0
    CHARGE = 1
    POP = 2
    VANISH = 3
    LINGER = 4
    GONE = 5
    R_LINGER = 6
    R_VANISH = 7
    R_POP = 8
    R_CHARGE = 9


@dataclasses.dataclass
class GokuState:
    phase: GokuPhase = GokuPhase.IDLE
    phase_start: float = 0.0
    holding: bool = False
    hold_start: float = 0.0
    scroll: float = 0.0
    seed_lines: list = dataclasses.field(default_factory=list)
    forehead_xy: tuple[int, int] | None = None


def _ease_in(u: float) -> float:
    return u * u * u


def _ease_out(u: float) -> float:
    return 1.0 - (1.0 - u) ** 3


def _phase_duration_ms(phase: GokuPhase, cfg: dict) -> float:
    if phase == GokuPhase.IDLE:
        return math.inf
    if phase == GokuPhase.GONE:
        return cfg["gone_ms"] if cfg["auto_reappear"] else math.inf
    mapping = {
        GokuPhase.CHARGE: cfg["charge_ms"],
        GokuPhase.POP: cfg["pop_ms"],
        GokuPhase.VANISH: cfg["vanish_ms"],
        GokuPhase.LINGER: cfg["linger_ms"],
        GokuPhase.R_LINGER: cfg["linger_ms"],
        GokuPhase.R_VANISH: cfg["vanish_ms"],
        GokuPhase.R_POP: cfg["pop_ms"],
        GokuPhase.R_CHARGE: cfg["charge_ms"],
    }
    return float(mapping[phase])


_PHASE_ORDER = [
    GokuPhase.IDLE,
    GokuPhase.CHARGE,
    GokuPhase.POP,
    GokuPhase.VANISH,
    GokuPhase.LINGER,
    GokuPhase.GONE,
    GokuPhase.R_LINGER,
    GokuPhase.R_VANISH,
    GokuPhase.R_POP,
    GokuPhase.R_CHARGE,
]


def regenerate_lines(state: GokuState, cfg: dict) -> None:
    """Resample the vertical line field. Called when entering CHARGE / R_LINGER."""
    n = max(int(cfg["line_density"]), 400)
    state.seed_lines = [
        {
            "x": random.random(),
            "y_offset": random.random(),
            "length": 0.3 + random.random() * 0.7,
            "speed": 0.6 + random.random() * 1.2,
        }
        for _ in range(n)
    ]


def enter_phase(state: GokuState, phase: GokuPhase, now: float, cfg: dict) -> None:
    state.phase = phase
    state.phase_start = now
    state.holding = False
    if phase in (GokuPhase.CHARGE, GokuPhase.R_LINGER):
        regenerate_lines(state, cfg)


def advance_phase(state: GokuState, now: float, cfg: dict) -> None:
    """Advance to the next phase when the current duration has elapsed."""
    if state.phase == GokuPhase.IDLE:
        return
    duration = _phase_duration_ms(state.phase, cfg)
    if duration == math.inf:
        return
    elapsed_ms = (now - state.phase_start) * 1000.0
    if elapsed_ms < duration:
        return
    idx = _PHASE_ORDER.index(state.phase)
    next_phase = _PHASE_ORDER[idx + 1] if idx + 1 < len(_PHASE_ORDER) else GokuPhase.IDLE
    enter_phase(state, next_phase, now, cfg)


def sample_envelopes(state: GokuState, now: float, cfg: dict) -> dict:
    """Match the mock's sampleEnvelopes verbatim."""
    phase = state.phase
    duration = _phase_duration_ms(phase, cfg)
    elapsed_ms = (now - state.phase_start) * 1000.0
    u = 0.0 if duration == math.inf else min(1.0, elapsed_ms / duration)

    env = {
        "silhouette_alpha": 1.0,
        "aura_intensity": 0.0,
        "line_intensity": 0.0,
        "line_mode": "normal",
        "flash": 0.0,
        "warp_amount": 0.0,
    }

    if phase == GokuPhase.IDLE:
        if state.holding:
            h = now - state.hold_start
            env["aura_intensity"] = min(1.0, h) * 0.4
            env["warp_amount"] = min(1.0, h) * 0.12
    elif phase == GokuPhase.CHARGE:
        env["aura_intensity"] = _ease_out(u)
        env["line_intensity"] = _ease_in(u) * 0.35
        env["warp_amount"] = _ease_in(u) * 0.3
    elif phase == GokuPhase.POP:
        env["aura_intensity"] = 1.0 - u * 0.6
        env["line_intensity"] = 1.0
        env["line_mode"] = "pop"
        env["flash"] = math.sin(u * math.pi)
        env["warp_amount"] = 0.5 + math.sin(u * math.pi) * 0.3
    elif phase == GokuPhase.VANISH:
        env["silhouette_alpha"] = 1.0 - _ease_in(u)
        env["aura_intensity"] = 0.4 * (1.0 - u)
        env["line_intensity"] = 1.0 - u * 0.3
        env["warp_amount"] = 0.3 * (1.0 - u)
    elif phase == GokuPhase.LINGER:
        env["silhouette_alpha"] = 0.0
        env["line_intensity"] = (1.0 - u) * 0.75
    elif phase == GokuPhase.GONE:
        env["silhouette_alpha"] = 0.0
    elif phase == GokuPhase.R_LINGER:
        env["silhouette_alpha"] = 0.0
        env["line_intensity"] = u * 0.75
    elif phase == GokuPhase.R_VANISH:
        env["silhouette_alpha"] = _ease_out(u)
        env["line_intensity"] = 0.75 - u * 0.3
        env["warp_amount"] = 0.25 * u
    elif phase == GokuPhase.R_POP:
        env["aura_intensity"] = (1.0 - u) * 0.6
        env["line_intensity"] = 0.4 * (1.0 - u)
        env["line_mode"] = "pop"
        env["flash"] = math.sin(u * math.pi) * 0.55
        env["warp_amount"] = 0.3 * (1.0 - u)
    elif phase == GokuPhase.R_CHARGE:
        env["aura_intensity"] = (1.0 - _ease_out(u)) * 0.5
        env["line_intensity"] = (1.0 - u) * 0.15
        env["warp_amount"] = (1.0 - u) * 0.1

    return env


# -------- Rendering --------


def draw_aura(frame: np.ndarray, head_center_xy: tuple[int, int] | None,
              intensity: float, max_radius: float) -> None:
    """Radial cyan ki glow around the forehead; alpha-blended onto frame in place."""
    if intensity <= 0.01 or head_center_xy is None:
        return
    height, width = frame.shape[:2]
    cx, cy = head_center_xy
    # Precompute distance field at a lower resolution for speed, then upscale.
    scale = 4
    small_w = max(1, width // scale)
    small_h = max(1, height // scale)
    y, x = np.ogrid[0:small_h, 0:small_w]
    sx = cx / scale
    sy = cy / scale
    sr = max(1.0, max_radius / scale)
    dist = np.sqrt((x - sx) ** 2 + (y - sy) ** 2) / sr
    dist = np.clip(dist, 0.0, 1.0)
    # Three-stop gradient matching the mock:
    #   r=0 → 0.35*intensity; r=0.3 → 0.18*intensity; r=1 → 0.
    alpha_small = np.where(
        dist < 0.3,
        0.35 - (0.35 - 0.18) * (dist / 0.3),
        0.18 * (1.0 - (dist - 0.3) / 0.7),
    ) * intensity
    alpha_small = np.clip(alpha_small, 0.0, 1.0).astype(np.float32)
    alpha = cv2.resize(alpha_small, (width, height), interpolation=cv2.INTER_LINEAR)
    alpha_3 = alpha[:, :, None]
    color = np.array(AURA_COLOR_BGR, dtype=np.float32)
    frame[:] = np.clip(
        frame.astype(np.float32) * (1.0 - alpha_3) + color * alpha_3,
        0, 255,
    ).astype(np.uint8)


def draw_lines_clipped(frame: np.ndarray, person_mask: np.ndarray,
                       state: GokuState, cfg: dict,
                       intensity: float, mode: str) -> None:
    """Draw vertical white lines clipped to the person mask, in place."""
    if intensity <= 0.01 or person_mask is None:
        return
    height, width = frame.shape[:2]
    layer = np.zeros((height, width), dtype=np.uint8)
    alpha_mult = min(1.0, intensity) * 0.9
    thickness = int(max(1, cfg["line_width"]))

    n = min(len(state.seed_lines), int(cfg["line_density"] * (0.6 + 0.4 * intensity)))
    for i in range(n):
        l = state.seed_lines[i]
        x = int(l["x"] * width)
        y_phase = (l["y_offset"] + state.scroll * l["speed"]) % 1.0
        y_top = int(y_phase * height - height * 0.3)
        y_end = y_top + int(height * l["length"])
        cv2.line(layer, (x, y_top), (x, y_end), 255, thickness)

    pop_mult = 0.0
    if mode == "pop":
        pop_mult = min(1.0, intensity)
        thick_pop = max(1, int(cfg["line_width"] * 1.8))
        for i in range(28):
            x = int((i / 28.0 + random.random() * 0.02) * width)
            cv2.line(layer, (x, 0), (x, height), 255, thick_pop)

    if layer.max() == 0:
        return

    # Composite: line_pixels * person_mask * alpha → white onto frame.
    line_alpha = layer.astype(np.float32) / 255.0 * max(alpha_mult, pop_mult)
    combined = (line_alpha * person_mask)[:, :, None]
    white = np.array([255.0, 255.0, 255.0], dtype=np.float32)
    frame[:] = np.clip(
        frame.astype(np.float32) * (1.0 - combined) + white * combined,
        0, 255,
    ).astype(np.uint8)


def warp_matrix(width: int, height: int, warp_amount: float, t_seconds: float) -> np.ndarray:
    """Affine matrix for the shaky teleport distortion.

    jitter_x = (rand-0.5)*warp*22; jitter_y = (rand-0.5)*warp*10;
    scale_y  = 1 + sin(t * 55.5) * warp * 0.045    (JS used sin(t_ms / 18), same thing in seconds).
    """
    jitter_x = (random.random() - 0.5) * warp_amount * 22.0
    jitter_y = (random.random() - 0.5) * warp_amount * 10.0
    scale_y = 1.0 + math.sin(t_seconds * 55.5) * warp_amount * 0.045
    cy = height * 0.5
    return np.array([
        [1.0, 0.0, jitter_x],
        [0.0, scale_y, jitter_y + cy * (1.0 - scale_y)],
    ], dtype=np.float32)


def apply_warp(frame: np.ndarray, warp_amount: float, t_seconds: float) -> np.ndarray:
    """Return a warped copy of frame. For small warps the overhead is minor."""
    if warp_amount <= 0.01:
        return frame
    height, width = frame.shape[:2]
    matrix = warp_matrix(width, height, warp_amount, t_seconds)
    return cv2.warpAffine(frame, matrix, (width, height),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def apply_warp_mask(mask: np.ndarray, warp_amount: float, t_seconds: float,
                    matrix: np.ndarray | None = None) -> np.ndarray:
    if warp_amount <= 0.01:
        return mask
    height, width = mask.shape[:2]
    m = matrix if matrix is not None else warp_matrix(width, height, warp_amount, t_seconds)
    return cv2.warpAffine(mask, m, (width, height),
                          flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)


def draw_flash(frame: np.ndarray, alpha: float) -> None:
    """White additive overlay, in place."""
    if alpha <= 0.01:
        return
    a = float(min(1.0, alpha * 0.6))
    frame[:] = cv2.addWeighted(
        np.full_like(frame, 255), a, frame, 1.0 - a, 0.0,
    )


# -------- Gesture detection --------


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _finger_extended(pts: list[tuple[float, float]], mcp: int, pip: int,
                     dip: int, tip: int, min_reach: float) -> bool:
    """Check that mcp→pip and dip→tip vectors are roughly aligned and reach is above threshold."""
    reach = _dist(pts[mcp], pts[tip])
    if reach < min_reach:
        return False
    v1x = pts[pip][0] - pts[mcp][0]
    v1y = pts[pip][1] - pts[mcp][1]
    v2x = pts[tip][0] - pts[dip][0]
    v2y = pts[tip][1] - pts[dip][1]
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 < 1e-3 or n2 < 1e-3:
        return False
    cosine = (v1x * v2x + v1y * v2y) / (n1 * n2)
    return cosine > 0.5


def forehead_from_face(face_result, img_wh: tuple[int, int]) -> tuple[int, int] | None:
    """Return the forehead screen position (landmark 10) if a face is detected."""
    if face_result is None or not getattr(face_result, "face_landmarks", None):
        return None
    width, height = img_wh
    face = face_result.face_landmarks[0]
    if len(face) <= 10:
        return None
    return int(face[10].x * width), int(face[10].y * height)


def detect_goku_gesture(face_result, hand_result, img_wh: tuple[int, int]) -> bool:
    """Index + middle extended and together, both near the forehead landmark."""
    if face_result is None or hand_result is None:
        return False
    if not getattr(face_result, "face_landmarks", None):
        return False
    if not getattr(hand_result, "hand_landmarks", None):
        return False

    width, height = img_wh
    face = face_result.face_landmarks[0]
    xs = [lm.x * width for lm in face]
    ys = [lm.y * height for lm in face]
    face_width = max(xs) - min(xs)
    if face_width < 20:
        return False
    forehead = (face[10].x * width, face[10].y * height)

    for hand in hand_result.hand_landmarks:
        if len(hand) != 21:
            continue
        pts = [(lm.x * width, lm.y * height) for lm in hand]
        index_tip = pts[8]
        middle_tip = pts[12]
        if _dist(index_tip, middle_tip) > face_width * 0.25:
            continue
        avg_tip = ((index_tip[0] + middle_tip[0]) * 0.5,
                   (index_tip[1] + middle_tip[1]) * 0.5)
        if _dist(avg_tip, forehead) > face_width * 0.35:
            continue
        if not _finger_extended(pts, 5, 6, 7, 8, face_width * 0.4):
            continue
        if not _finger_extended(pts, 9, 10, 11, 12, face_width * 0.4):
            continue
        # Ring and pinky should NOT be as extended as index (loose check).
        ring_reach = _dist(pts[13], pts[16])
        pinky_reach = _dist(pts[17], pts[20])
        index_reach = _dist(pts[5], pts[8])
        if ring_reach > index_reach * 0.9 or pinky_reach > index_reach * 0.9:
            continue
        return True
    return False
