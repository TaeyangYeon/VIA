"""
Generate VIA app icons for Electron packaging.
Requires: Pillow  (pip install Pillow)

Outputs:
  frontend/build/icons/icon.png   — 512x512 (Linux fallback)
  frontend/build/icons/icon.icns  — macOS iconset
  frontend/build/icons/icon.ico   — Windows multi-size ICO
"""
import io
import os
import struct
import sys
import zlib
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not found. Install with: pip install Pillow --break-system-packages")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
ICON_DIR = SCRIPT_DIR.parent / "frontend" / "build" / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

BG_COLOR = (10, 10, 10, 255)       # #0a0a0a
TEXT_COLOR = (245, 245, 245, 255)   # #f5f5f5


def make_base_image(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to load a bold font at a reasonable size; fall back to default
    font_size = int(size * 0.38)
    font = None
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                candidate = ImageFont.truetype(path, font_size)
                # Quick validation: ensure getbbox works (some TTC files are broken)
                test_draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
                test_draw.textbbox((0, 0), "VIA", font=candidate)
                font = candidate
                break
            except Exception:
                pass

    text = "VIA"
    if font:
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (size - tw) // 2 - bbox[0]
            y = (size - th) // 2 - bbox[1]
            draw.text((x, y), text, fill=TEXT_COLOR, font=font)
        except Exception:
            # Fallback to default PIL font
            draw.text((size // 4, size // 3), text, fill=TEXT_COLOR)
    else:
        # PIL default font — small but guaranteed
        draw.text((size // 4, size // 3), text, fill=TEXT_COLOR)

    return img


# ── PNG 512×512 ───────────────────────────────────────────────────────────────

def generate_png():
    img = make_base_image(512)
    out = ICON_DIR / "icon.png"
    img.save(out, "PNG")
    print(f"  Created {out} ({img.size[0]}x{img.size[1]})")


# ── ICO (Windows, multi-size) ─────────────────────────────────────────────────

def generate_ico():
    sizes = [16, 32, 48, 64, 128, 256]
    images = [make_base_image(s).convert("RGBA") for s in sizes]
    out = ICON_DIR / "icon.ico"
    # Save the largest as base; Pillow will embed all sizes
    images[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"  Created {out} ({len(sizes)} sizes: {sizes})")


# ── ICNS (macOS) ──────────────────────────────────────────────────────────────
# Pillow does not write .icns directly, so we construct it manually.
# ICNS format: magic 'icns' + total length (4 bytes), then a list of chunks.
# Each chunk: OSType (4 bytes) + chunk length incl. header (4 bytes) + PNG data.
#
# Supported OSType → pixel size mapping (PNG representations, macOS 10.7+):
#   icp4  16x16    icp5  32x32    icp6  64x64
#   ic07  128x128  ic08  256x256  ic09  512x512  ic10 1024x1024

ICNS_TYPES = [
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
]


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_icns():
    chunks = b""
    for ostype, size in ICNS_TYPES:
        img = make_base_image(size)
        png_data = image_to_png_bytes(img)
        header = ostype.encode("ascii") + struct.pack(">I", len(png_data) + 8)
        chunks += header + png_data

    total_len = 8 + len(chunks)
    icns_data = b"icns" + struct.pack(">I", total_len) + chunks

    out = ICON_DIR / "icon.icns"
    out.write_bytes(icns_data)
    print(f"  Created {out} ({len(icns_data)} bytes, {len(ICNS_TYPES)} sizes)")


if __name__ == "__main__":
    print("Generating VIA app icons...")
    generate_png()
    generate_ico()
    generate_icns()
    print("Done.")
