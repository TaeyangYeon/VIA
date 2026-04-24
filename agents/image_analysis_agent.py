"""Image analysis agent for computing ImageDiagnosis metrics using OpenCV."""

from typing import Optional

import cv2
import numpy as np

from agents.base_agent import BaseAgent
from agents.models import (
    DefectScale,
    IlluminationType,
    ImageDiagnosis,
    NoiseFrequency,
)


class ImageAnalysisAgent(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("image_analysis", directive)

    def execute(self, image: np.ndarray) -> ImageDiagnosis:
        directive = self.get_directive()
        if directive:
            self._log("INFO", "Agent directive active", {"directive": directive})

        gray = self._to_gray(image)
        is_color = image.ndim == 3 and image.shape[2] == 3

        contrast = self._compute_contrast(gray)
        noise_level = self._compute_noise_level(gray)
        edge_density = self._compute_edge_density(gray)
        lighting_uniformity = self._compute_lighting_uniformity(gray)
        illumination_type = self._compute_illumination_type(gray, lighting_uniformity)
        noise_frequency = self._compute_noise_frequency(gray)
        reflection_level = self._compute_reflection_level(gray)
        texture_complexity = self._compute_texture_complexity(gray)
        edge_sharpness = self._compute_edge_sharpness(gray)
        blob_feasibility, blob_count_estimate, blob_size_variance, threshold_candidate = (
            self._compute_blob_metrics(gray)
        )
        color_discriminability = self._compute_color_discriminability(image, is_color, gray)
        dominant_channel_ratio = self._compute_dominant_channel_ratio(image, is_color)
        structural_regularity = self._compute_structural_regularity(gray)
        pattern_repetition = self._compute_pattern_repetition(gray)
        background_uniformity = self._compute_background_uniformity(gray)
        surface_type = self._classify_surface(texture_complexity, reflection_level, edge_density)
        defect_scale = self._classify_defect_scale(edge_density, blob_count_estimate, blob_size_variance)
        optimal_color_space = self._compute_optimal_color_space(
            is_color, color_discriminability, surface_type
        )

        return ImageDiagnosis(
            contrast=contrast,
            noise_level=noise_level,
            edge_density=edge_density,
            lighting_uniformity=lighting_uniformity,
            illumination_type=illumination_type,
            noise_frequency=noise_frequency,
            reflection_level=reflection_level,
            texture_complexity=texture_complexity,
            surface_type=surface_type,
            defect_scale=defect_scale,
            blob_feasibility=blob_feasibility,
            blob_count_estimate=blob_count_estimate,
            blob_size_variance=blob_size_variance,
            color_discriminability=color_discriminability,
            dominant_channel_ratio=dominant_channel_ratio,
            structural_regularity=structural_regularity,
            pattern_repetition=pattern_repetition,
            background_uniformity=background_uniformity,
            optimal_color_space=optimal_color_space,
            threshold_candidate=threshold_candidate,
            edge_sharpness=edge_sharpness,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        if not np.isfinite(value):
            return lo
        return max(lo, min(hi, value))

    # ── Metric computations ───────────────────────────────────────────────────

    def _compute_contrast(self, gray: np.ndarray) -> float:
        return self._clamp(float(np.std(gray.astype(np.float32))) / 255.0)

    def _compute_noise_level(self, gray: np.ndarray) -> float:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        diff = gray.astype(np.float32) - blurred.astype(np.float32)
        return self._clamp(float(np.std(diff)) / 50.0)

    def _compute_edge_density(self, gray: np.ndarray) -> float:
        edges = cv2.Canny(gray, 50, 150)
        total = float(gray.shape[0] * gray.shape[1])
        if total == 0:
            return 0.0
        return self._clamp(float(np.count_nonzero(edges)) / total)

    def _compute_lighting_uniformity(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        grid = 4
        cell_h = max(1, h // grid)
        cell_w = max(1, w // grid)
        means = []
        for i in range(grid):
            for j in range(grid):
                cell = gray[i * cell_h : (i + 1) * cell_h, j * cell_w : (j + 1) * cell_w]
                if cell.size > 0:
                    means.append(float(np.mean(cell)))
        if not means:
            return 1.0
        mean_val = float(np.mean(means))
        if mean_val < 1e-6:
            return 1.0
        cv = float(np.std(means)) / mean_val
        return self._clamp(1.0 - cv)

    def _compute_illumination_type(self, gray: np.ndarray, uniformity: float) -> IlluminationType:
        if uniformity > 0.85:
            return IlluminationType.uniform
        h, w = gray.shape
        f = gray.astype(np.float32)
        cy_s = max(0, h // 2 - h // 6)
        cy_e = min(h, h // 2 + h // 6)
        cx_s = max(0, w // 2 - w // 6)
        cx_e = min(w, w // 2 + w // 6)
        overall_mean = float(np.mean(f)) if f.size > 0 else 1.0
        if cy_e > cy_s and cx_e > cx_s:
            center_mean = float(np.mean(f[cy_s:cy_e, cx_s:cx_e]))
        else:
            center_mean = overall_mean
        spot_ratio = center_mean / (overall_mean + 1e-6)
        if spot_ratio > 1.5 or spot_ratio < 0.67:
            return IlluminationType.spot
        col_std = float(np.std(np.mean(f, axis=0)))
        row_std = float(np.std(np.mean(f, axis=1)))
        if max(col_std, row_std) > 30:
            return IlluminationType.gradient
        return IlluminationType.uneven

    def _compute_noise_frequency(self, gray: np.ndarray) -> NoiseFrequency:
        f = np.fft.fft2(gray.astype(np.float32))
        magnitude = np.abs(np.fft.fftshift(f))
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2
        r_low = max(1, min(h, w) // 8)
        yy, xx = np.ogrid[:h, :w]
        mask_low = (yy - cy) ** 2 + (xx - cx) ** 2 <= r_low ** 2
        total_energy = float(np.sum(magnitude))
        if total_energy < 1e-6:
            return NoiseFrequency.low_freq
        low_energy = float(np.sum(magnitude[mask_low]))
        high_energy = total_energy - low_energy
        if high_energy > low_energy:
            return NoiseFrequency.high_freq
        return NoiseFrequency.low_freq

    def _compute_reflection_level(self, gray: np.ndarray) -> float:
        total = float(gray.size)
        if total == 0:
            return 0.0
        return self._clamp(float(np.count_nonzero(gray >= 250)) / total)

    def _compute_texture_complexity(self, gray: np.ndarray) -> float:
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return self._clamp(float(np.var(lap)) / 5000.0)

    def _compute_edge_sharpness(self, gray: np.ndarray) -> float:
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        val = float(np.var(lap))
        return val if np.isfinite(val) else 0.0

    def _compute_blob_metrics(self, gray: np.ndarray) -> tuple:
        try:
            thresh_val, thresh_img = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            threshold_candidate = float(thresh_val)
            contours, _ = cv2.findContours(
                thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            min_area = max(1.0, gray.size * 0.001)
            valid = [c for c in contours if cv2.contourArea(c) >= min_area]
            count = len(valid)
            if count > 0:
                areas = np.array([cv2.contourArea(c) for c in valid], dtype=np.float64)
                area_var = float(np.var(areas))
                max_sq = float(gray.size) ** 2
                blob_size_variance = self._clamp(area_var / (max_sq + 1e-6))
                feasibility = self._clamp(min(count, 20) / 20.0 * 0.5 + 0.5)
            else:
                blob_size_variance = 0.0
                feasibility = 0.1
            return feasibility, count, blob_size_variance, threshold_candidate
        except Exception:
            return 0.0, 0, 0.0, 128.0

    def _compute_color_discriminability(
        self, image: np.ndarray, is_color: bool, gray: np.ndarray
    ) -> float:
        if not is_color:
            if int(gray.max()) == int(gray.min()):
                return 0.0
            otsu_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            threshold = int(otsu_val)
            below = gray < threshold
            above = ~below
            if not (np.any(below) and np.any(above)):
                return 0.0
            w0 = float(np.sum(below)) / gray.size
            w1 = 1.0 - w0
            mu0 = float(np.mean(gray[below]))
            mu1 = float(np.mean(gray[above]))
            between_var = w0 * w1 * (mu0 - mu1) ** 2
            total_var = float(np.var(gray.astype(np.float32)))
            if total_var < 1e-6:
                return 0.0
            return self._clamp(between_var / (total_var + 1e-6))
        channel_means = [float(np.mean(image[:, :, i])) for i in range(3)]
        max_sep = float(max(channel_means) - min(channel_means))
        return self._clamp(max_sep / 255.0)

    def _compute_dominant_channel_ratio(self, image: np.ndarray, is_color: bool) -> float:
        if not is_color:
            return 1.0
        channel_means = [float(np.mean(image[:, :, i])) for i in range(3)]
        total = sum(channel_means)
        if total < 1e-6:
            return 1.0 / 3.0
        return self._clamp(max(channel_means) / total)

    def _compute_structural_regularity(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        if h < 16 or w < 16:
            return 0.5
        size = min(h, w) // 4
        regions = []
        for i in range(0, h - size + 1, size):
            for j in range(0, w - size + 1, size):
                patch = gray[i : i + size, j : j + size]
                resized = cv2.resize(patch, (16, 16), interpolation=cv2.INTER_AREA)
                regions.append(resized.flatten().astype(np.float32))
        if len(regions) < 2:
            return 0.5
        base = regions[0]
        base_std = float(np.std(base))
        if base_std < 1e-6:
            return 1.0
        correlations = []
        for r in regions[1:]:
            r_std = float(np.std(r))
            if r_std < 1e-6:
                continue
            corr = float(np.corrcoef(base, r)[0, 1])
            if np.isfinite(corr):
                correlations.append(abs(corr))
        if not correlations:
            return 0.5
        return self._clamp(float(np.mean(correlations)))

    def _compute_pattern_repetition(self, gray: np.ndarray) -> float:
        h, w = gray.shape
        if h < 4 or w < 4:
            return 0.0
        norm = gray.astype(np.float32) - float(np.mean(gray))
        norms = float(np.sum(norm ** 2))
        if norms < 1e-6:
            return 1.0
        shifts = [h // 4, h // 3, h // 2]
        max_corr = 0.0
        for shift in shifts:
            if shift <= 0 or shift >= h:
                continue
            shifted = np.roll(norm, shift, axis=0)
            corr = float(np.sum(norm * shifted)) / norms
            if np.isfinite(corr):
                max_corr = max(max_corr, abs(corr))
        return self._clamp(max_corr)

    def _compute_background_uniformity(self, gray: np.ndarray) -> float:
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        mode_val = int(np.argmax(hist))
        margin = 20
        lo = max(0, mode_val - margin)
        hi = min(255, mode_val + margin)
        bg_mask = (gray >= lo) & (gray <= hi)
        bg_pixels = gray[bg_mask].astype(np.float32)
        if len(bg_pixels) < 10:
            return 0.5
        mean_val = float(np.mean(bg_pixels))
        if mean_val < 1e-6:
            return 1.0
        cv = float(np.std(bg_pixels)) / mean_val
        return self._clamp(1.0 - cv * 2)

    # ── Classification ────────────────────────────────────────────────────────

    @staticmethod
    def _classify_surface(
        texture: float, reflection: float, edge_density: float
    ) -> str:
        if reflection > 0.3 and texture < 0.3:
            return "glass"
        if reflection > 0.2 and texture < 0.5:
            return "metal"
        if edge_density > 0.2 and texture > 0.3:
            return "pcb"
        if texture > 0.4 and reflection < 0.1:
            return "fabric"
        if texture < 0.2 and reflection < 0.2:
            return "plastic"
        return "unknown"

    @staticmethod
    def _classify_defect_scale(
        edge_density: float, blob_count: int, blob_size_var: float
    ) -> DefectScale:
        if blob_count > 10 or blob_size_var > 0.5:
            return DefectScale.micro
        if blob_count > 0 and blob_size_var < 0.3:
            return DefectScale.macro
        if edge_density > 0.1:
            return DefectScale.texture
        return DefectScale.macro

    @staticmethod
    def _compute_optimal_color_space(
        is_color: bool, color_discriminability: float, surface_type: str
    ) -> str:
        if not is_color:
            return "gray"
        if color_discriminability > 0.3:
            return "hsv_s"
        if surface_type in ("metal", "glass"):
            return "lab_l"
        return "rgb"
