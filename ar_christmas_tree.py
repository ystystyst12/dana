"""Webcam-based hand gesture AR that renders a festive Christmas tree overlay.

The script uses MediaPipe to detect a single hand in the camera feed. Raising an
open hand (four or more extended fingers) shows the tree, while a closed fist
with one or fewer fingers extended hides it. The tree is anchored to the
detected hand position and scales with the hand size to maintain a stable
augmented reality effect.

Usage::

    python ar_christmas_tree.py

Keyboard shortcuts:
    - ``q`` or ``ESC``: quit the application.

Dependencies are listed in ``requirements.txt``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class HandState:
    """Lightweight representation of a detected hand's state."""

    center: tuple[int, int]
    scale: float
    fingers_extended: int


def detect_hand_state(
    hand_landmarks: mp.framework.formats.landmark_pb2.NormalizedLandmarkList,
    image_shape: tuple[int, int],
) -> HandState:
    """Compute hand center, scale, and finger count from MediaPipe landmarks."""

    height, width = image_shape
    coords = np.array(
        [(int(lm.x * width), int(lm.y * height)) for lm in hand_landmarks.landmark]
    )

    wrist = coords[0]
    middle_mcp = coords[9]
    center = ((wrist[0] + middle_mcp[0]) // 2, (wrist[1] + middle_mcp[1]) // 2)

    bbox_min = coords.min(axis=0)
    bbox_max = coords.max(axis=0)
    bbox_width, bbox_height = bbox_max - bbox_min
    scale = max(bbox_width, bbox_height, 1) / 200.0

    fingers_extended = _count_extended_fingers(coords)
    return HandState(center=center, scale=scale, fingers_extended=fingers_extended)


def _count_extended_fingers(coords: np.ndarray) -> int:
    """Count extended fingers with simple vector geometry heuristics."""

    finger_tips = [4, 8, 12, 16, 20]
    finger_pips = [2, 6, 10, 14, 18]

    extended = 0
    for tip, pip in zip(finger_tips, finger_pips):
        tip_y = coords[tip][1]
        pip_y = coords[pip][1]
        if tip == 4:
            tip_x, pip_x = coords[tip][0], coords[pip][0]
            if tip_x - pip_x > 20:
                extended += 1
        elif tip_y < pip_y - 10:
            extended += 1
    return extended


def draw_christmas_tree(frame: np.ndarray, center: tuple[int, int], scale: float) -> None:
    """Draw a layered Christmas tree anchored at ``center`` onto the ``frame``."""

    overlay = frame.copy()
    base_height = int(220 * scale)
    base_width = int(160 * scale)

    cx, cy = center
    trunk_height = int(base_height * 0.2)
    trunk_width = int(base_width * 0.2)

    trunk_top = cy + base_height // 2
    trunk_rect = (
        (cx - trunk_width // 2, trunk_top),
        (cx + trunk_width // 2, trunk_top + trunk_height),
    )
    cv2.rectangle(overlay, trunk_rect[0], trunk_rect[1], (60, 40, 25), thickness=-1)

    layers = 3
    for i in range(layers):
        layer_height = int(base_height * 0.28)
        layer_top = cy + base_height // 2 - (i + 1) * layer_height + 10 * i
        width_factor = 1.0 - i * 0.2
        half_width = int(base_width * width_factor // 2)
        pts = np.array(
            [
                (cx, layer_top - layer_height),
                (cx - half_width, layer_top + 10),
                (cx + half_width, layer_top + 10),
            ],
            np.int32,
        )
        cv2.fillPoly(overlay, [pts], color=(34, 139, 34))
        _draw_ornaments(overlay, pts)

    star_radius = int(16 * scale)
    _draw_star(overlay, (cx, cy - base_height // 2 - star_radius), star_radius)

    alpha = 0.85
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)


def _draw_ornaments(overlay: np.ndarray, triangle_pts: np.ndarray) -> None:
    """Scatter small ornaments on a triangle layer."""

    min_x, min_y = triangle_pts[:, 0].min(), triangle_pts[:, 1].min()
    max_x, max_y = triangle_pts[:, 0].max(), triangle_pts[:, 1].max()

    rng = np.random.default_rng(42)
    ornaments = rng.integers(low=[min_x, min_y], high=[max_x, max_y], size=(6, 2))
    colors = [(0, 215, 255), (0, 0, 255), (255, 255, 0), (255, 105, 180)]

    for (x, y) in ornaments:
        cv2.circle(
            overlay,
            (int(x), int(y)),
            radius=6,
            color=colors[(x + y) % len(colors)],
            thickness=-1,
        )


def _draw_star(overlay: np.ndarray, center: tuple[int, int], radius: int) -> None:
    """Render a simple five-point star above the tree."""

    cx, cy = center
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius // 2
        x = int(cx + r * math.cos(angle))
        y = int(cy - r * math.sin(angle))
        points.append((x, y))
    cv2.fillPoly(overlay, [np.array(points, np.int32)], color=(0, 215, 255))


def main() -> None:
    mp_hands = mp.solutions.hands
    hand_detector = mp_hands.Hands(
        max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Unable to open the default camera (index 0).")

    show_tree = False
    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hand_detector.process(rgb_frame)

        if results.multi_hand_landmarks:
            hand_state = detect_hand_state(
                results.multi_hand_landmarks[0], frame.shape[:2]
            )
            if hand_state.fingers_extended >= 4:
                show_tree = True
            elif hand_state.fingers_extended <= 1:
                show_tree = False

            cv2.putText(
                frame,
                f"Fingers: {hand_state.fingers_extended}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            if show_tree:
                draw_christmas_tree(frame, hand_state.center, hand_state.scale)
        else:
            cv2.putText(
                frame,
                "Show an open hand to place the tree",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        cv2.putText(
            frame,
            "Fist to hide, open hand to show | q/ESC to quit",
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow("Christmas Tree AR", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

    hand_detector.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
