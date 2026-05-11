"""Processing quality evaluator for rapid pipeline candidate filtering."""
from __future__ import annotations

import cv2
import numpy as np


class ProcessingQualityEvaluator:
    def evaluate(self, original: np.ndarray, processed: np.ndarray) -> dict:
        orig = self._to_gray(original)
        proc = self._to_gray(processed)

        contrast = self._contrast_preservation(orig, proc)
        edge = self._edge_retention(orig, proc)
        noise = self._noise_reduction_score(orig, proc)
        detail = self._detail_preservation(orig, proc)
        overall = 0.3 * contrast + 0.25 * edge + 0.25 * noise + 0.2 * detail

        return {
            "contrast_preservation": float(np.clip(contrast, 0.0, 1.0)),
            "edge_retention": float(np.clip(edge, 0.0, 1.0)),
            "noise_reduction_score": float(np.clip(noise, 0.0, 1.0)),
            "detail_preservation": float(np.clip(detail, 0.0, 1.0)),
            "overall_score": float(np.clip(overall, 0.0, 1.0)),
        }

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    @staticmethod
    def _contrast_preservation(orig: np.ndarray, proc: np.ndarray) -> float:
        orig_std = float(np.std(orig.astype(np.float32)))
        if orig_std == 0.0:
            return 1.0
        proc_std = float(np.std(proc.astype(np.float32)))
        return min(proc_std / orig_std, 1.0)

    @staticmethod
    def _edge_retention(orig: np.ndarray, proc: np.ndarray) -> float:
        orig_edges = int(np.count_nonzero(cv2.Canny(orig, 50, 150)))
        if orig_edges == 0:
            return 1.0
        proc_edges = int(np.count_nonzero(cv2.Canny(proc, 50, 150)))
        return min(proc_edges / orig_edges, 1.0)

    @staticmethod
    def _noise_level(image: np.ndarray) -> float:
        blurred = cv2.GaussianBlur(image, (0, 0), 1.0)
        diff = image.astype(np.float32) - blurred.astype(np.float32)
        return float(np.std(diff))

    def _noise_reduction_score(self, orig: np.ndarray, proc: np.ndarray) -> float:
        orig_noise = self._noise_level(orig)
        if orig_noise == 0.0:
            return 1.0
        proc_noise = self._noise_level(proc)
        return max(0.0, 1.0 - proc_noise / orig_noise)

    def _detail_preservation(self, orig: np.ndarray, proc: np.ndarray) -> float:
        h, w = orig.shape
        patch_size = max(16, min(h, w) // 4)

        if h < patch_size or w < patch_size:
            return 1.0

        scores = []
        for i in range(0, h - patch_size + 1, patch_size):
            for j in range(0, w - patch_size + 1, patch_size):
                orig_patch = orig[i : i + patch_size, j : j + patch_size]

                if float(np.std(orig_patch)) < 1e-6:
                    scores.append(1.0)
                    continue

                if proc.shape[0] < patch_size or proc.shape[1] < patch_size:
                    scores.append(1.0)
                    continue

                result = cv2.matchTemplate(proc, orig_patch, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                scores.append(float(np.clip(max_val, 0.0, 1.0)))

        if not scores:
            return 1.0
        return float(np.mean(scores))
