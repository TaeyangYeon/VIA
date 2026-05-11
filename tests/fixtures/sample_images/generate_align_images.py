"""Generate synthetic align test images for E2E testing.

Images have a bright white circle + crosshair on a dark background.
Ground truth coordinates are encoded in the filename: X_{float}_Y_{float}_{index}.png

Run: python tests/fixtures/sample_images/generate_align_images.py
Produces: X_320.0_Y_240.0_1.png, X_160.0_Y_120.0_2.png, X_480.0_Y_360.0_3.png, X_250.5_Y_200.5_4.png
"""
import os

import cv2
import numpy as np

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
W, H = 640, 480
_CIRCLE_RADIUS = 30
_RNG = np.random.default_rng(42)


def _dark_canvas() -> np.ndarray:
    """Dark background with slight noise to simulate a real scene."""
    return _RNG.integers(10, 30, size=(H, W), dtype=np.uint8)


def generate_align_images() -> list[tuple[str, np.ndarray]]:
    specs = [
        (320.0, 240.0, 1),   # image center
        (160.0, 120.0, 2),   # top-left quadrant
        (480.0, 360.0, 3),   # bottom-right quadrant
        (250.5, 200.5, 4),   # fractional-offset position
    ]
    images = []
    for cx, cy, idx in specs:
        img = _dark_canvas()
        ix, iy = int(round(cx)), int(round(cy))
        # Bright white filled circle — primary alignment target
        cv2.circle(img, (ix, iy), _CIRCLE_RADIUS, 255, -1)
        # Crosshair lines — increase structural identifiability for edge-detection methods
        cv2.line(img, (ix - 50, iy), (ix + 50, iy), 200, 2)
        cv2.line(img, (ix, iy - 50), (ix, iy + 50), 200, 2)
        fname = f"X_{cx}_Y_{cy}_{idx}.png"
        images.append((fname, img))
    return images


def main() -> None:
    all_images = generate_align_images()
    for filename, img in all_images:
        path = os.path.join(OUTPUT_DIR, filename)
        cv2.imwrite(path, img)
        print(f"Generated: {path}")
    print(f"Done — {len(all_images)} images generated.")


if __name__ == "__main__":
    main()
