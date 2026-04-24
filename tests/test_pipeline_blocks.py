"""Tests for Pipeline Block Library (Step 14)."""
import numpy as np
import pytest
import cv2

from agents.models import (
    DefectScale,
    IlluminationType,
    ImageDiagnosis,
    NoiseFrequency,
)
from agents.pipeline_blocks import BlockDefinition, PipelineBlockLibrary, block_library


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_diagnosis(**kwargs) -> ImageDiagnosis:
    defaults = {
        "contrast": 0.5,
        "noise_level": 0.3,
        "edge_density": 0.1,
        "lighting_uniformity": 0.8,
        "illumination_type": IlluminationType.uniform,
        "noise_frequency": NoiseFrequency.high_freq,
        "reflection_level": 0.1,
        "texture_complexity": 0.3,
        "surface_type": "plastic",
        "defect_scale": DefectScale.macro,
        "blob_feasibility": 0.3,
        "blob_count_estimate": 5,
        "blob_size_variance": 0.1,
        "color_discriminability": 0.3,
        "dominant_channel_ratio": 0.4,
        "structural_regularity": 0.4,
        "pattern_repetition": 0.3,
        "background_uniformity": 0.7,
        "optimal_color_space": "rgb",
        "threshold_candidate": 128.0,
        "edge_sharpness": 100.0,
    }
    defaults.update(kwargs)
    return ImageDiagnosis(**defaults)


np.random.seed(42)
COLOR_IMG = np.random.randint(50, 200, (64, 64, 3), dtype=np.uint8)
GRAY_IMG = np.random.randint(50, 200, (64, 64), dtype=np.uint8)

ALL_BLOCK_PARAMS: dict[str, dict] = {
    "grayscale": {},
    "hsv_s": {},
    "lab_l": {},
    "gaussian_fine": {"sigma": 0.3},
    "gaussian_mid": {"sigma": 1.0},
    "bilateral": {"d": 5, "sigmaColor": 25},
    "median": {"k": 3},
    "nlmeans": {"h": 3},
    "clahe": {"clip": 1.0},
    "otsu": {},
    "adaptive_mean": {"blockSize": 11},
    "adaptive_gauss": {"blockSize": 11},
    "erosion": {"k": 3, "iterations": 1},
    "dilation": {"k": 3, "iterations": 1},
    "opening": {"k": 3},
    "closing": {"k": 3},
    "tophat": {"k": 3},
    "blackhat": {"k": 3},
    "canny": {"t1": 30, "t2": 100},
    "sobel": {"ksize": 3},
    "laplacian": {"ksize": 3},
}


# ── Section 1: BlockDefinition Structure ──────────────────────────────────────

class TestBlockDefinitionStructure:
    def test_name_is_string(self):
        b = block_library.get_block("grayscale")
        assert isinstance(b.name, str) and b.name == "grayscale"

    def test_category_is_known_value(self):
        for name in ALL_BLOCK_PARAMS:
            b = block_library.get_block(name)
            assert b.category in {"color_space", "noise_reduction", "threshold", "morphology", "edge"}

    def test_params_is_dict(self):
        b = block_library.get_block("gaussian_fine")
        assert isinstance(b.params, dict)

    def test_apply_is_callable(self):
        b = block_library.get_block("canny")
        assert callable(b.apply)

    def test_matches_is_callable(self):
        b = block_library.get_block("canny")
        assert callable(b.matches)


# ── Section 2: apply() output validity (all blocks, color input) ──────────────

@pytest.mark.parametrize("name,params", list(ALL_BLOCK_PARAMS.items()))
def test_apply_color_returns_valid_ndarray(name, params):
    b = block_library.get_block(name)
    result = b.apply(COLOR_IMG.copy(), params)
    assert isinstance(result, np.ndarray), f"{name}: result is not ndarray"
    assert result.size > 0, f"{name}: result is empty"
    assert np.isfinite(result.astype(np.float32)).all(), f"{name}: result has NaN/Inf"


# ── Section 3: apply() edge cases (grayscale / color-conversion) ──────────────

class TestApplyEdgeCases:
    def test_grayscale_block_converts_color_to_2d(self):
        b = block_library.get_block("grayscale")
        result = b.apply(COLOR_IMG.copy(), {})
        assert result.ndim == 2

    def test_grayscale_block_keeps_gray_as_2d(self):
        b = block_library.get_block("grayscale")
        result = b.apply(GRAY_IMG.copy(), {})
        assert result.ndim == 2

    def test_hsv_s_on_grayscale_returns_2d_unchanged(self):
        b = block_library.get_block("hsv_s")
        result = b.apply(GRAY_IMG.copy(), {})
        assert result.ndim == 2

    def test_otsu_on_color_returns_binary_2d(self):
        b = block_library.get_block("otsu")
        result = b.apply(COLOR_IMG.copy(), {})
        assert result.ndim == 2
        unique_vals = set(np.unique(result).tolist())
        assert unique_vals.issubset({0, 255}), f"otsu output has unexpected values: {unique_vals}"


# ── Section 4: matches() True conditions ─────────────────────────────────────

class TestMatchesTrue:
    def test_grayscale_matches_low_color_discriminability(self):
        d = make_diagnosis(color_discriminability=0.1)
        assert block_library.get_block("grayscale").matches(d) is True

    def test_hsv_s_matches_high_color_discriminability(self):
        d = make_diagnosis(color_discriminability=0.6)
        assert block_library.get_block("hsv_s").matches(d) is True

    def test_lab_l_matches_metal_surface(self):
        d = make_diagnosis(surface_type="metal")
        assert block_library.get_block("lab_l").matches(d) is True

    def test_gaussian_fine_matches_low_noise(self):
        d = make_diagnosis(noise_level=0.1)
        assert block_library.get_block("gaussian_fine").matches(d) is True

    def test_gaussian_mid_matches_mid_range_noise(self):
        d = make_diagnosis(noise_level=0.35)
        assert block_library.get_block("gaussian_mid").matches(d) is True

    def test_bilateral_matches_high_reflection(self):
        d = make_diagnosis(reflection_level=0.5)
        assert block_library.get_block("bilateral").matches(d) is True

    def test_clahe_matches_uneven_illumination(self):
        d = make_diagnosis(illumination_type=IlluminationType.uneven)
        assert block_library.get_block("clahe").matches(d) is True

    def test_otsu_matches_sufficient_contrast(self):
        d = make_diagnosis(contrast=0.3)
        assert block_library.get_block("otsu").matches(d) is True

    def test_adaptive_mean_matches_gradient_illumination(self):
        d = make_diagnosis(illumination_type=IlluminationType.gradient)
        assert block_library.get_block("adaptive_mean").matches(d) is True

    def test_adaptive_gauss_matches_uneven_illumination(self):
        d = make_diagnosis(illumination_type=IlluminationType.uneven)
        assert block_library.get_block("adaptive_gauss").matches(d) is True

    def test_tophat_matches_micro_defect(self):
        d = make_diagnosis(defect_scale=DefectScale.micro)
        assert block_library.get_block("tophat").matches(d) is True

    def test_blackhat_matches_micro_defect_with_contrast(self):
        d = make_diagnosis(defect_scale=DefectScale.micro, contrast=0.3)
        assert block_library.get_block("blackhat").matches(d) is True

    def test_canny_always_matches(self):
        d = make_diagnosis(contrast=0.0, noise_level=0.0, edge_density=0.0)
        assert block_library.get_block("canny").matches(d) is True

    def test_sobel_matches_high_structural_regularity(self):
        d = make_diagnosis(structural_regularity=0.6)
        assert block_library.get_block("sobel").matches(d) is True

    def test_laplacian_matches_sufficient_edge_density(self):
        d = make_diagnosis(edge_density=0.2)
        assert block_library.get_block("laplacian").matches(d) is True


# ── Section 5: matches() False conditions ────────────────────────────────────

class TestMatchesFalse:
    def test_grayscale_does_not_match_high_color_discriminability(self):
        d = make_diagnosis(color_discriminability=0.4)
        assert block_library.get_block("grayscale").matches(d) is False

    def test_lab_l_does_not_match_non_metal_surface(self):
        d = make_diagnosis(surface_type="plastic")
        assert block_library.get_block("lab_l").matches(d) is False

    def test_gaussian_fine_does_not_match_noise_at_boundary(self):
        d = make_diagnosis(noise_level=0.2)
        assert block_library.get_block("gaussian_fine").matches(d) is False

    def test_blackhat_does_not_match_without_micro_defect(self):
        d = make_diagnosis(defect_scale=DefectScale.macro, contrast=0.5)
        assert block_library.get_block("blackhat").matches(d) is False

    def test_sobel_does_not_match_low_structural_regularity(self):
        d = make_diagnosis(structural_regularity=0.4)
        assert block_library.get_block("sobel").matches(d) is False


# ── Section 6: PipelineBlockLibrary methods ───────────────────────────────────

class TestPipelineBlockLibrary:
    def test_get_block_by_name(self):
        b = block_library.get_block("canny")
        assert b.name == "canny"

    def test_get_block_raises_keyerror_on_unknown(self):
        with pytest.raises(KeyError):
            block_library.get_block("nonexistent_block_xyz")

    def test_get_all_blocks_returns_21(self):
        assert len(block_library.get_all_blocks()) == 21

    def test_get_categories_returns_exactly_5(self):
        cats = set(block_library.get_categories())
        assert cats == {"color_space", "noise_reduction", "threshold", "morphology", "edge"}

    def test_get_blocks_by_category_color_space(self):
        blocks = block_library.get_blocks_by_category("color_space")
        assert len(blocks) == 3
        assert all(b.category == "color_space" for b in blocks)

    def test_get_matching_blocks_returns_expected_blocks(self):
        # noise_level=0.1 → gaussian_fine; contrast=0.3 → otsu; canny always
        d = make_diagnosis(contrast=0.3, noise_level=0.1)
        matched_names = [b.name for b in block_library.get_matching_blocks(d)]
        assert "gaussian_fine" in matched_names
        assert "otsu" in matched_names
        assert "canny" in matched_names

    def test_get_matching_blocks_with_category_filter(self):
        d = make_diagnosis(noise_level=0.1)
        matched = block_library.get_matching_blocks(d, category="noise_reduction")
        assert all(b.category == "noise_reduction" for b in matched)
        assert "gaussian_fine" in [b.name for b in matched]


# ── Section 7: Parameter space correctness ────────────────────────────────────

class TestParameterSpaces:
    def test_grayscale_has_empty_params(self):
        b = block_library.get_block("grayscale")
        assert b.params == {}

    def test_gaussian_fine_sigma_values(self):
        b = block_library.get_block("gaussian_fine")
        assert b.params["sigma"] == [0.3, 0.5, 0.8]

    def test_bilateral_has_d_and_sigmaColor(self):
        b = block_library.get_block("bilateral")
        assert set(b.params.keys()) == {"d", "sigmaColor"}
        assert b.params["sigmaColor"] == [25, 50, 75]

    def test_erosion_has_k_and_iterations(self):
        b = block_library.get_block("erosion")
        assert "k" in b.params
        assert b.params["iterations"] == [1, 2, 3]

    def test_canny_has_t1_and_t2(self):
        b = block_library.get_block("canny")
        assert b.params["t1"] == [30, 50, 100]
        assert b.params["t2"] == [100, 150, 200]


# ── Section 8: Singleton ──────────────────────────────────────────────────────

def test_singleton_is_prepopulated_library():
    assert isinstance(block_library, PipelineBlockLibrary)
    assert len(block_library.get_all_blocks()) == 21
