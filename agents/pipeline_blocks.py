"""Pipeline block library with condition-based matching rules."""
from __future__ import annotations

from typing import Callable

import cv2
import numpy as np

from agents.models import DefectScale, IlluminationType, ImageDiagnosis


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def _is_color(image: np.ndarray) -> bool:
    return image.ndim == 3 and image.shape[2] >= 1


# ── Apply functions ───────────────────────────────────────────────────────────

def _apply_grayscale(image: np.ndarray, params: dict) -> np.ndarray:
    return _ensure_gray(image)


def _apply_hsv_s(image: np.ndarray, params: dict) -> np.ndarray:
    if not _is_color(image):
        return image
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return hsv[:, :, 1]


def _apply_lab_l(image: np.ndarray, params: dict) -> np.ndarray:
    if not _is_color(image):
        return image
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    return lab[:, :, 0]


def _apply_gaussian_fine(image: np.ndarray, params: dict) -> np.ndarray:
    sigma = float(params.get("sigma", 0.5))
    return cv2.GaussianBlur(image, (0, 0), sigma)


def _apply_gaussian_mid(image: np.ndarray, params: dict) -> np.ndarray:
    sigma = float(params.get("sigma", 1.0))
    return cv2.GaussianBlur(image, (0, 0), sigma)


def _apply_bilateral(image: np.ndarray, params: dict) -> np.ndarray:
    d = int(params.get("d", 5))
    sigma_color = float(params.get("sigmaColor", 25))
    return cv2.bilateralFilter(image, d, sigma_color, sigma_color)


def _apply_median(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    return cv2.medianBlur(image, k)


def _apply_nlmeans(image: np.ndarray, params: dict) -> np.ndarray:
    h = float(params.get("h", 3))
    if _is_color(image):
        return cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)
    return cv2.fastNlMeansDenoising(image, None, h, 7, 21)


def _apply_clahe(image: np.ndarray, params: dict) -> np.ndarray:
    clip = float(params.get("clip", 2.0))
    gray = _ensure_gray(image)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _apply_otsu(image: np.ndarray, params: dict) -> np.ndarray:
    gray = _ensure_gray(image)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def _apply_adaptive_mean(image: np.ndarray, params: dict) -> np.ndarray:
    block_size = int(params.get("blockSize", 11))
    gray = _ensure_gray(image)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, block_size, 2
    )


def _apply_adaptive_gauss(image: np.ndarray, params: dict) -> np.ndarray:
    block_size = int(params.get("blockSize", 11))
    gray = _ensure_gray(image)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, 2
    )


def _apply_erosion(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    iterations = int(params.get("iterations", 1))
    gray = _ensure_gray(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.erode(gray, kernel, iterations=iterations)


def _apply_dilation(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    iterations = int(params.get("iterations", 1))
    gray = _ensure_gray(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.dilate(gray, kernel, iterations=iterations)


def _apply_opening(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    gray = _ensure_gray(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)


def _apply_closing(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    gray = _ensure_gray(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)


def _apply_tophat(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    gray = _ensure_gray(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)


def _apply_blackhat(image: np.ndarray, params: dict) -> np.ndarray:
    k = int(params.get("k", 3))
    gray = _ensure_gray(image)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    return cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)


def _apply_canny(image: np.ndarray, params: dict) -> np.ndarray:
    t1 = float(params.get("t1", 50))
    t2 = float(params.get("t2", 150))
    gray = _ensure_gray(image)
    return cv2.Canny(gray, t1, t2)


def _apply_sobel(image: np.ndarray, params: dict) -> np.ndarray:
    ksize = int(params.get("ksize", 3))
    gray = _ensure_gray(image)
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
    magnitude = np.abs(sx) + np.abs(sy)
    return np.clip(magnitude, 0, 255).astype(np.uint8)


def _apply_laplacian(image: np.ndarray, params: dict) -> np.ndarray:
    ksize = int(params.get("ksize", 3))
    gray = _ensure_gray(image)
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
    return cv2.convertScaleAbs(lap)


# ── BlockDefinition ───────────────────────────────────────────────────────────

class BlockDefinition:
    def __init__(
        self,
        name: str,
        category: str,
        params: dict,
        apply: Callable[[np.ndarray, dict], np.ndarray],
        matches: Callable[[ImageDiagnosis], bool],
    ):
        self.name = name
        self.category = category
        self.params = params
        self.apply = apply
        self.matches = matches


# ── PipelineBlockLibrary ──────────────────────────────────────────────────────

class PipelineBlockLibrary:
    def __init__(self) -> None:
        self._blocks: dict[str, BlockDefinition] = {}
        self._register_all()

    def _register(self, block: BlockDefinition) -> None:
        self._blocks[block.name] = block

    def get_block(self, name: str) -> BlockDefinition:
        if name not in self._blocks:
            raise KeyError(f"Block '{name}' not found in library")
        return self._blocks[name]

    def get_all_blocks(self) -> list[BlockDefinition]:
        return list(self._blocks.values())

    def get_categories(self) -> list[str]:
        return list(dict.fromkeys(b.category for b in self._blocks.values()))

    def get_blocks_by_category(self, category: str) -> list[BlockDefinition]:
        return [b for b in self._blocks.values() if b.category == category]

    def get_matching_blocks(
        self, diagnosis: ImageDiagnosis, category: str | None = None
    ) -> list[BlockDefinition]:
        result = []
        for block in self._blocks.values():
            if category is not None and block.category != category:
                continue
            if block.matches(diagnosis):
                result.append(block)
        return result

    def _register_all(self) -> None:
        # ── Color space ──────────────────────────────────────────────────────
        self._register(BlockDefinition(
            name="grayscale",
            category="color_space",
            params={},
            apply=_apply_grayscale,
            matches=lambda d: d.color_discriminability < 0.3,
        ))
        self._register(BlockDefinition(
            name="hsv_s",
            category="color_space",
            params={},
            apply=_apply_hsv_s,
            matches=lambda d: d.color_discriminability > 0.5,
        ))
        self._register(BlockDefinition(
            name="lab_l",
            category="color_space",
            params={},
            apply=_apply_lab_l,
            matches=lambda d: d.surface_type == "metal",
        ))

        # ── Noise reduction ───────────────────────────────────────────────────
        self._register(BlockDefinition(
            name="gaussian_fine",
            category="noise_reduction",
            params={"sigma": [0.3, 0.5, 0.8]},
            apply=_apply_gaussian_fine,
            matches=lambda d: d.noise_level < 0.2,
        ))
        self._register(BlockDefinition(
            name="gaussian_mid",
            category="noise_reduction",
            params={"sigma": [1.0, 1.5, 2.0]},
            apply=_apply_gaussian_mid,
            matches=lambda d: 0.2 <= d.noise_level <= 0.5,
        ))
        self._register(BlockDefinition(
            name="bilateral",
            category="noise_reduction",
            params={"d": [5, 9], "sigmaColor": [25, 50, 75]},
            apply=_apply_bilateral,
            matches=lambda d: d.reflection_level > 0.4,
        ))
        self._register(BlockDefinition(
            name="median",
            category="noise_reduction",
            params={"k": [3, 5, 7]},
            apply=_apply_median,
            matches=lambda d: d.noise_level > 0.3,
        ))
        self._register(BlockDefinition(
            name="nlmeans",
            category="noise_reduction",
            params={"h": [3, 6, 10]},
            apply=_apply_nlmeans,
            matches=lambda d: d.noise_level > 0.6,
        ))
        self._register(BlockDefinition(
            name="clahe",
            category="noise_reduction",
            params={"clip": [1.0, 2.0, 4.0]},
            apply=_apply_clahe,
            matches=lambda d: d.illumination_type == IlluminationType.uneven,
        ))

        # ── Threshold ─────────────────────────────────────────────────────────
        self._register(BlockDefinition(
            name="otsu",
            category="threshold",
            params={},
            apply=_apply_otsu,
            matches=lambda d: d.contrast > 0.15,
        ))
        self._register(BlockDefinition(
            name="adaptive_mean",
            category="threshold",
            params={"blockSize": [11, 21, 31]},
            apply=_apply_adaptive_mean,
            matches=lambda d: d.illumination_type in (
                IlluminationType.gradient, IlluminationType.uneven
            ),
        ))
        self._register(BlockDefinition(
            name="adaptive_gauss",
            category="threshold",
            params={"blockSize": [11, 21, 31]},
            apply=_apply_adaptive_gauss,
            matches=lambda d: d.illumination_type in (
                IlluminationType.gradient, IlluminationType.uneven
            ),
        ))

        # ── Morphology ────────────────────────────────────────────────────────
        self._register(BlockDefinition(
            name="erosion",
            category="morphology",
            params={"k": [3, 5], "iterations": [1, 2, 3]},
            apply=_apply_erosion,
            matches=lambda d: d.noise_level > 0.2,
        ))
        self._register(BlockDefinition(
            name="dilation",
            category="morphology",
            params={"k": [3, 5], "iterations": [1, 2, 3]},
            apply=_apply_dilation,
            matches=lambda d: d.blob_feasibility > 0.3,
        ))
        self._register(BlockDefinition(
            name="opening",
            category="morphology",
            params={"k": [3, 5]},
            apply=_apply_opening,
            matches=lambda d: d.noise_level > 0.2,
        ))
        self._register(BlockDefinition(
            name="closing",
            category="morphology",
            params={"k": [3, 5]},
            apply=_apply_closing,
            matches=lambda d: d.blob_feasibility > 0.3,
        ))
        self._register(BlockDefinition(
            name="tophat",
            category="morphology",
            params={"k": [3, 5, 7]},
            apply=_apply_tophat,
            matches=lambda d: d.defect_scale == DefectScale.micro,
        ))
        self._register(BlockDefinition(
            name="blackhat",
            category="morphology",
            params={"k": [3, 5, 7]},
            apply=_apply_blackhat,
            matches=lambda d: d.defect_scale == DefectScale.micro and d.contrast > 0.2,
        ))

        # ── Edge ──────────────────────────────────────────────────────────────
        self._register(BlockDefinition(
            name="canny",
            category="edge",
            params={"t1": [30, 50, 100], "t2": [100, 150, 200]},
            apply=_apply_canny,
            matches=lambda d: True,
        ))
        self._register(BlockDefinition(
            name="sobel",
            category="edge",
            params={"ksize": [3, 5]},
            apply=_apply_sobel,
            matches=lambda d: d.structural_regularity > 0.5,
        ))
        self._register(BlockDefinition(
            name="laplacian",
            category="edge",
            params={"ksize": [1, 3, 5]},
            apply=_apply_laplacian,
            matches=lambda d: d.edge_density > 0.1,
        ))


# ── Singleton ─────────────────────────────────────────────────────────────────

block_library = PipelineBlockLibrary()
