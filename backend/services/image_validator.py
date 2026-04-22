"""Image validation service for upload filename, extension, size, and integrity checks."""

import re
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
FILENAME_PATTERN = re.compile(r"^(OK|NG)_([1-9]\d*)\.\w+$")


@dataclass
class ValidationResult:
    valid: bool
    filename: str
    error: Optional[str] = None
    label: Optional[str] = None
    index: Optional[int] = None


class ImageValidator:
    """Validates uploaded image files."""

    @staticmethod
    def validate_filename(filename: str) -> ValidationResult:
        match = FILENAME_PATTERN.match(filename)
        if not match:
            return ValidationResult(
                valid=False,
                filename=filename,
                error=f"Invalid filename '{filename}'. Must match OK_N.ext or NG_N.ext (N >= 1).",
            )
        label = match.group(1)
        index = int(match.group(2))
        return ValidationResult(
            valid=True, filename=filename, label=label, index=index
        )

    @staticmethod
    def validate_extension(filename: str) -> bool:
        dot_pos = filename.rfind(".")
        if dot_pos == -1:
            return False
        ext = filename[dot_pos:].lower()
        return ext in ALLOWED_EXTENSIONS

    @staticmethod
    def validate_file_size(content: bytes) -> bool:
        return len(content) <= MAX_FILE_SIZE

    @staticmethod
    def validate_image_integrity(content: bytes) -> bool:
        arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        return img is not None
