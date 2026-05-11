"""Tests for ImageAnalysisAgent — Step 13."""

import math

import cv2
import numpy as np
import pytest

from agents.base_agent import BaseAgent
from agents.models import DefectScale, IlluminationType, ImageDiagnosis, NoiseFrequency


# ── Image factories ───────────────────────────────────────────────────────────

def gray(value: int, size=(100, 100)) -> np.ndarray:
    return np.full(size, value, dtype=np.uint8)


def color_bicolor(size=(100, 100, 3)) -> np.ndarray:
    img = np.zeros(size, dtype=np.uint8)
    img[: size[0] // 2, :, 2] = 200   # top half red (BGR: ch2=R)
    img[size[0] // 2 :, :, 0] = 200   # bottom half blue
    return img


def random_noise(size=(100, 100, 3), seed=42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size, dtype=np.uint8)


def horizontal_gradient(size=(100, 100)) -> np.ndarray:
    h, w = size
    return np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))


def striped(size=(100, 100, 3)) -> np.ndarray:
    img = np.zeros(size, dtype=np.uint8)
    for i in range(0, size[0], 2):
        img[i, :, :] = 255
    return img


def blobs() -> np.ndarray:
    img = np.full((200, 200, 3), 200, dtype=np.uint8)
    cv2.circle(img, (50, 50), 20, (0, 0, 0), -1)
    cv2.circle(img, (150, 50), 15, (0, 0, 0), -1)
    cv2.circle(img, (100, 150), 25, (0, 0, 0), -1)
    return img


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def agent():
    from agents.image_analysis_agent import ImageAnalysisAgent
    return ImageAnalysisAgent()


# ── Class structure ───────────────────────────────────────────────────────────

class TestClassStructure:
    def test_inherits_base_agent(self, agent):
        assert isinstance(agent, BaseAgent)

    def test_agent_name_is_image_analysis(self, agent):
        assert agent.agent_name == "image_analysis"

    def test_execute_is_callable(self, agent):
        assert callable(agent.execute)

    def test_execute_is_not_coroutine(self, agent):
        import inspect
        img = gray(128)
        result = agent.execute(img)
        assert not inspect.iscoroutine(result)

    def test_execute_returns_image_diagnosis(self, agent):
        result = agent.execute(gray(128))
        assert isinstance(result, ImageDiagnosis)

    def test_constructor_accepts_directive(self):
        from agents.image_analysis_agent import ImageAnalysisAgent
        a = ImageAnalysisAgent(directive="focus on edges")
        assert a.get_directive() == "focus on edges"

    def test_default_directive_is_none(self, agent):
        assert agent.get_directive() is None

    def test_execute_accepts_keyword_argument(self, agent):
        result = agent.execute(image=gray(128))
        assert isinstance(result, ImageDiagnosis)


# ── Contrast ──────────────────────────────────────────────────────────────────

class TestContrast:
    def test_uniform_image_has_zero_contrast(self, agent):
        assert agent.execute(gray(128)).contrast == pytest.approx(0.0, abs=0.01)

    def test_bimodal_image_has_high_contrast(self, agent):
        img = gray(0)
        img[50:, :] = 255
        assert agent.execute(img).contrast > agent.execute(gray(128)).contrast

    def test_contrast_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).contrast <= 1.0


# ── Noise level ───────────────────────────────────────────────────────────────

class TestNoiseLevel:
    def test_smooth_image_has_low_noise(self, agent):
        assert agent.execute(gray(128)).noise_level < 0.3

    def test_random_noise_has_measurable_noise(self, agent):
        assert agent.execute(random_noise()).noise_level > 0.1

    def test_noise_level_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).noise_level <= 1.0


# ── Edge density ──────────────────────────────────────────────────────────────

class TestEdgeDensity:
    def test_flat_image_has_low_edge_density(self, agent):
        assert agent.execute(gray(128)).edge_density < 0.1

    def test_striped_image_has_edges(self, agent):
        # Canny with internal Gaussian blur reduces thin-stripe density; > 0.01 is sufficient
        assert agent.execute(striped()).edge_density > 0.01

    def test_edge_density_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).edge_density <= 1.0


# ── Lighting uniformity ───────────────────────────────────────────────────────

class TestLightingUniformity:
    def test_uniform_image_has_high_uniformity(self, agent):
        assert agent.execute(gray(128)).lighting_uniformity > 0.8

    def test_gradient_has_lower_uniformity_than_flat(self, agent):
        flat = agent.execute(gray(128)).lighting_uniformity
        grad = agent.execute(horizontal_gradient()).lighting_uniformity
        assert flat >= grad

    def test_lighting_uniformity_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).lighting_uniformity <= 1.0


# ── Illumination type ─────────────────────────────────────────────────────────

class TestIlluminationType:
    def test_uniform_image_returns_uniform_type(self, agent):
        assert agent.execute(gray(128)).illumination_type == IlluminationType.uniform

    def test_illumination_type_is_valid_enum(self, agent):
        result = agent.execute(random_noise()).illumination_type
        assert isinstance(result, IlluminationType)
        assert result in IlluminationType


# ── Noise frequency ───────────────────────────────────────────────────────────

class TestNoiseFrequency:
    def test_random_noise_is_high_freq(self, agent):
        assert agent.execute(random_noise()).noise_frequency == NoiseFrequency.high_freq

    def test_noise_frequency_is_valid_enum(self, agent):
        result = agent.execute(random_noise()).noise_frequency
        assert isinstance(result, NoiseFrequency)
        assert result in NoiseFrequency


# ── Reflection level ──────────────────────────────────────────────────────────

class TestReflectionLevel:
    def test_black_image_has_zero_reflection(self, agent):
        assert agent.execute(np.zeros((100, 100, 3), dtype=np.uint8)).reflection_level == pytest.approx(0.0, abs=0.01)

    def test_white_image_has_high_reflection(self, agent):
        assert agent.execute(np.full((100, 100, 3), 255, dtype=np.uint8)).reflection_level > 0.9

    def test_reflection_level_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).reflection_level <= 1.0


# ── Texture complexity ────────────────────────────────────────────────────────

class TestTextureComplexity:
    def test_smooth_image_has_low_texture(self, agent):
        assert agent.execute(gray(128)).texture_complexity < 0.5

    def test_noisy_has_more_texture_than_smooth(self, agent):
        assert agent.execute(random_noise()).texture_complexity >= agent.execute(gray(128)).texture_complexity

    def test_texture_complexity_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).texture_complexity <= 1.0


# ── Surface type ──────────────────────────────────────────────────────────────

_VALID_SURFACES = {"metal", "plastic", "pcb", "fabric", "glass", "unknown"}


class TestSurfaceType:
    def test_surface_type_is_valid_string(self, agent):
        assert agent.execute(random_noise()).surface_type in _VALID_SURFACES

    def test_surface_type_for_flat_image(self, agent):
        assert agent.execute(gray(128)).surface_type in _VALID_SURFACES


# ── Defect scale ──────────────────────────────────────────────────────────────

class TestDefectScale:
    def test_defect_scale_is_valid_enum(self, agent):
        result = agent.execute(random_noise()).defect_scale
        assert isinstance(result, DefectScale)
        assert result in DefectScale


# ── Blob metrics ──────────────────────────────────────────────────────────────

class TestBlobMetrics:
    def test_blob_feasibility_in_range(self, agent):
        assert 0.0 <= agent.execute(blobs()).blob_feasibility <= 1.0

    def test_blob_count_is_non_negative_int(self, agent):
        result = agent.execute(blobs())
        assert isinstance(result.blob_count_estimate, int)
        assert result.blob_count_estimate >= 0

    def test_blob_size_variance_in_range(self, agent):
        assert 0.0 <= agent.execute(blobs()).blob_size_variance <= 1.0

    def test_flat_image_has_few_blobs(self, agent):
        assert agent.execute(gray(128)).blob_count_estimate <= 5


# ── Color metrics ─────────────────────────────────────────────────────────────

class TestColorMetrics:
    def test_color_discriminability_in_range(self, agent):
        assert 0.0 <= agent.execute(color_bicolor()).color_discriminability <= 1.0

    def test_dominant_channel_ratio_in_range(self, agent):
        assert 0.0 <= agent.execute(color_bicolor()).dominant_channel_ratio <= 1.0

    def test_grayscale_dominant_channel_ratio_is_one(self, agent):
        assert agent.execute(gray(128)).dominant_channel_ratio == pytest.approx(1.0, abs=0.01)


# ── Structural metrics ────────────────────────────────────────────────────────

class TestStructuralMetrics:
    def test_structural_regularity_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).structural_regularity <= 1.0

    def test_pattern_repetition_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).pattern_repetition <= 1.0

    def test_background_uniformity_in_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).background_uniformity <= 1.0

    def test_flat_image_has_high_background_uniformity(self, agent):
        assert agent.execute(gray(128)).background_uniformity > 0.5


# ── Optimal color space ───────────────────────────────────────────────────────

_VALID_COLOR_SPACES = {"gray", "hsv_s", "lab_l", "rgb"}


class TestOptimalColorSpace:
    def test_optimal_color_space_is_valid(self, agent):
        assert agent.execute(random_noise()).optimal_color_space in _VALID_COLOR_SPACES

    def test_grayscale_input_recommends_gray(self, agent):
        assert agent.execute(gray(128)).optimal_color_space == "gray"


# ── Threshold candidate ───────────────────────────────────────────────────────

class TestThresholdCandidate:
    def test_threshold_in_0_255_range(self, agent):
        assert 0.0 <= agent.execute(random_noise()).threshold_candidate <= 255.0

    def test_black_image_threshold_is_low(self, agent):
        assert agent.execute(np.zeros((100, 100, 3), dtype=np.uint8)).threshold_candidate < 10.0


# ── Edge sharpness ────────────────────────────────────────────────────────────

class TestEdgeSharpness:
    def test_edge_sharpness_non_negative(self, agent):
        assert agent.execute(random_noise()).edge_sharpness >= 0.0

    def test_blurred_image_has_lower_sharpness(self, agent):
        sharp = striped()
        blurred = cv2.GaussianBlur(sharp, (15, 15), 5.0)
        assert agent.execute(sharp).edge_sharpness >= agent.execute(blurred).edge_sharpness


# ── Edge cases ────────────────────────────────────────────────────────────────

_FLOAT_FIELDS = [
    "contrast", "noise_level", "edge_density", "lighting_uniformity",
    "reflection_level", "texture_complexity", "blob_feasibility",
    "blob_size_variance", "color_discriminability", "dominant_channel_ratio",
    "structural_regularity", "pattern_repetition", "background_uniformity",
    "threshold_candidate", "edge_sharpness",
]


class TestEdgeCases:
    def test_grayscale_2d_input_returns_image_diagnosis(self, agent):
        assert isinstance(agent.execute(gray(128)), ImageDiagnosis)

    def test_tiny_10x10_does_not_crash(self, agent):
        assert isinstance(agent.execute(np.zeros((10, 10, 3), dtype=np.uint8)), ImageDiagnosis)

    def test_all_black_does_not_crash(self, agent):
        assert isinstance(agent.execute(np.zeros((100, 100, 3), dtype=np.uint8)), ImageDiagnosis)

    def test_all_white_does_not_crash(self, agent):
        assert isinstance(agent.execute(np.full((100, 100, 3), 255, dtype=np.uint8)), ImageDiagnosis)

    @pytest.mark.parametrize("img", [
        np.zeros((100, 100, 3), dtype=np.uint8),
        np.full((100, 100, 3), 255, dtype=np.uint8),
        random_noise(),
        gray(128),
    ])
    def test_all_floats_are_finite(self, agent, img):
        result = agent.execute(img)
        for field in _FLOAT_FIELDS:
            val = getattr(result, field)
            assert math.isfinite(val), f"{field} is not finite"

    def test_tiny_image_all_floats_finite(self, agent):
        result = agent.execute(np.zeros((10, 10, 3), dtype=np.uint8))
        for field in _FLOAT_FIELDS:
            assert math.isfinite(getattr(result, field)), f"{field} not finite for tiny image"


# ── Full execute integration ──────────────────────────────────────────────────

class TestFullExecute:
    def test_returns_image_diagnosis_from_color_image(self, agent):
        assert isinstance(agent.execute(color_bicolor()), ImageDiagnosis)

    def test_all_21_fields_have_correct_types(self, agent):
        r = agent.execute(color_bicolor())
        assert isinstance(r.contrast, float)
        assert isinstance(r.noise_level, float)
        assert isinstance(r.edge_density, float)
        assert isinstance(r.lighting_uniformity, float)
        assert isinstance(r.illumination_type, IlluminationType)
        assert isinstance(r.noise_frequency, NoiseFrequency)
        assert isinstance(r.reflection_level, float)
        assert isinstance(r.texture_complexity, float)
        assert isinstance(r.surface_type, str)
        assert isinstance(r.defect_scale, DefectScale)
        assert isinstance(r.blob_feasibility, float)
        assert isinstance(r.blob_count_estimate, int)
        assert isinstance(r.blob_size_variance, float)
        assert isinstance(r.color_discriminability, float)
        assert isinstance(r.dominant_channel_ratio, float)
        assert isinstance(r.structural_regularity, float)
        assert isinstance(r.pattern_repetition, float)
        assert isinstance(r.background_uniformity, float)
        assert isinstance(r.optimal_color_space, str)
        assert isinstance(r.threshold_candidate, float)
        assert isinstance(r.edge_sharpness, float)

    def test_directive_does_not_raise(self):
        from agents.image_analysis_agent import ImageAnalysisAgent
        a = ImageAnalysisAgent(directive="analyze carefully")
        assert isinstance(a.execute(color_bicolor()), ImageDiagnosis)

    def test_noisy_image_has_nonzero_noise_level(self, agent):
        assert agent.execute(random_noise()).noise_level > 0.0
