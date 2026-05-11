"""Generate synthetic test images for E2E testing of circle detection inspection.

Run: python tests/fixtures/sample_images/generate_sample_images.py
Produces: OK_1..OK_3, NG_1..NG_3 as 640x480 grayscale PNGs.
"""
import os

import cv2
import numpy as np

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
W, H = 640, 480


def _canvas() -> np.ndarray:
    return np.full((H, W), 255, dtype=np.uint8)


def generate_ok_images() -> list[tuple[str, np.ndarray]]:
    specs = [
        ((320, 240), 50),
        ((315, 245), 52),
        ((325, 235), 48),
    ]
    images = []
    for i, ((cx, cy), r) in enumerate(specs, start=1):
        img = _canvas()
        cv2.circle(img, (cx, cy), r, 0, -1)
        images.append((f"OK_{i}.png", img))
    return images


def generate_ng_images() -> list[tuple[str, np.ndarray]]:
    images = []

    # NG_1: blank — no circle present
    images.append(("NG_1.png", _canvas()))

    # NG_2: deformed ellipse instead of circle
    img = _canvas()
    cv2.ellipse(img, (320, 240), (80, 30), 0, 0, 360, 0, -1)
    images.append(("NG_2.png", img))

    # NG_3: two circles — multiple shapes, violates single-circle spec
    img = _canvas()
    cv2.circle(img, (160, 120), 40, 0, -1)
    cv2.circle(img, (480, 360), 40, 0, -1)
    images.append(("NG_3.png", img))

    return images


def main() -> None:
    all_images = generate_ok_images() + generate_ng_images()
    for filename, img in all_images:
        path = os.path.join(OUTPUT_DIR, filename)
        cv2.imwrite(path, img)
        print(f"Generated: {path}")
    print(f"Done — {len(all_images)} images generated.")


if __name__ == "__main__":
    main()
