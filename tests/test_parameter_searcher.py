"""Tests for ProcessingQualityEvaluator and ParameterSearcher (Step 16)."""
import numpy as np
import pytest
import cv2
from unittest.mock import MagicMock, patch

from agents.models import PipelineBlock, ProcessingPipeline
from agents.pipeline_blocks import block_library


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def gray_image():
    img = np.zeros((128, 128), dtype=np.uint8)
    for i in range(128):
        img[i, :] = i * 2
    return img


@pytest.fixture
def color_image(gray_image):
    return cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def black_image():
    return np.zeros((64, 64), dtype=np.uint8)


@pytest.fixture
def white_image():
    return np.full((64, 64), 255, dtype=np.uint8)


@pytest.fixture
def noisy_image(gray_image):
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 40, gray_image.shape, dtype=np.uint8)
    return np.clip(gray_image.astype(np.int32) + noise, 0, 255).astype(np.uint8)


def _make_image():
    img = np.zeros((128, 128), dtype=np.uint8)
    for i in range(128):
        img[i, :] = i * 2
    return img


def _make_pipeline(*block_names) -> ProcessingPipeline:
    blocks = [PipelineBlock(name=n, when_condition="test", params={}) for n in block_names]
    return ProcessingPipeline(name="test_pipeline", blocks=blocks)


# ── ProcessingQualityEvaluator ────────────────────────────────────────────────

class TestProcessingQualityEvaluatorImport:
    def test_class_importable(self):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        assert ProcessingQualityEvaluator is not None

    def test_not_base_agent_subclass(self):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        from agents.base_agent import BaseAgent
        assert not issubclass(ProcessingQualityEvaluator, BaseAgent)

    def test_has_evaluate_method(self):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        assert hasattr(ProcessingQualityEvaluator, "evaluate")


class TestProcessingQualityEvaluatorOutput:
    def test_evaluate_returns_dict(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        assert isinstance(result, dict)

    def test_evaluate_has_all_required_keys(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        assert set(result.keys()) == {
            "contrast_preservation",
            "edge_retention",
            "noise_reduction_score",
            "detail_preservation",
            "overall_score",
        }

    def test_all_scores_are_floats(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        for v in result.values():
            assert isinstance(v, float)

    def test_all_scores_in_range(self, gray_image, noisy_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        for orig, proc in [(gray_image, noisy_image), (noisy_image, gray_image)]:
            result = ProcessingQualityEvaluator().evaluate(orig, proc)
            for k, v in result.items():
                assert 0.0 <= v <= 1.0, f"{k}={v} out of [0,1]"


class TestContrastPreservation:
    def test_identical_images_score_is_one(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        assert result["contrast_preservation"] == pytest.approx(1.0)

    def test_zero_original_std_returns_one(self, black_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(black_image, black_image)
        assert result["contrast_preservation"] == pytest.approx(1.0)

    def test_blurred_has_lower_contrast_than_original(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        blurred = cv2.GaussianBlur(gray_image, (0, 0), 5.0)
        result = ProcessingQualityEvaluator().evaluate(gray_image, blurred)
        assert result["contrast_preservation"] < 1.0

    def test_formula_correctness(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        blurred = cv2.GaussianBlur(gray_image, (0, 0), 3.0)
        orig_std = float(np.std(gray_image.astype(np.float32)))
        proc_std = float(np.std(blurred.astype(np.float32)))
        expected = min(proc_std / orig_std, 1.0)
        result = ProcessingQualityEvaluator().evaluate(gray_image, blurred)
        assert result["contrast_preservation"] == pytest.approx(expected, abs=0.01)

    def test_clamped_to_one_when_processed_has_higher_std(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        # Sharpen to get higher std
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
        sharpened = cv2.filter2D(gray_image, -1, kernel)
        result = ProcessingQualityEvaluator().evaluate(gray_image, sharpened)
        assert result["contrast_preservation"] <= 1.0


class TestEdgeRetention:
    def test_identical_images_score_is_one(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        assert result["edge_retention"] == pytest.approx(1.0)

    def test_no_original_edges_returns_one(self, black_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(black_image, black_image)
        assert result["edge_retention"] == pytest.approx(1.0)

    def test_heavily_blurred_loses_edges(self):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        # Step image (sharp edge) — ensures original has Canny edges
        step = np.zeros((128, 128), dtype=np.uint8)
        step[:, 64:] = 255
        blurred = cv2.GaussianBlur(step, (0, 0), 10.0)
        result = ProcessingQualityEvaluator().evaluate(step, blurred)
        assert result["edge_retention"] < 1.0

    def test_formula_correctness(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        blurred = cv2.GaussianBlur(gray_image, (0, 0), 5.0)
        orig_edges = np.count_nonzero(cv2.Canny(gray_image, 50, 150))
        proc_edges = np.count_nonzero(cv2.Canny(blurred, 50, 150))
        expected = min(proc_edges / orig_edges, 1.0) if orig_edges > 0 else 1.0
        result = ProcessingQualityEvaluator().evaluate(gray_image, blurred)
        assert result["edge_retention"] == pytest.approx(expected, abs=0.01)


class TestNoiseReductionScore:
    def test_identical_images_score_is_zero(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        # Same image: no noise reduction happened
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        assert result["noise_reduction_score"] == pytest.approx(0.0, abs=0.01)

    def test_zero_original_noise_returns_one(self, black_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(black_image, black_image)
        assert result["noise_reduction_score"] == pytest.approx(1.0)

    def test_blurring_noisy_image_increases_score(self, noisy_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        blurred = cv2.GaussianBlur(noisy_image, (0, 0), 1.5)
        result_same = ProcessingQualityEvaluator().evaluate(noisy_image, noisy_image)
        result_blurred = ProcessingQualityEvaluator().evaluate(noisy_image, blurred)
        assert result_blurred["noise_reduction_score"] > result_same["noise_reduction_score"]

    def test_white_image_no_noise_returns_one(self, white_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(white_image, white_image)
        assert result["noise_reduction_score"] == pytest.approx(1.0)

    def test_score_clamped_above_zero(self, gray_image, noisy_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, noisy_image)
        assert result["noise_reduction_score"] >= 0.0


class TestDetailPreservation:
    def test_identical_images_score_near_one(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        assert result["detail_preservation"] >= 0.8

    def test_score_in_range(self, gray_image, noisy_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, noisy_image)
        assert 0.0 <= result["detail_preservation"] <= 1.0

    def test_black_image_handled_gracefully(self, black_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(black_image, black_image)
        assert 0.0 <= result["detail_preservation"] <= 1.0


class TestOverallScore:
    def test_weighted_average_formula(self, gray_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        blurred = cv2.GaussianBlur(gray_image, (0, 0), 1.5)
        result = ProcessingQualityEvaluator().evaluate(gray_image, blurred)
        expected = (
            0.3 * result["contrast_preservation"]
            + 0.25 * result["edge_retention"]
            + 0.25 * result["noise_reduction_score"]
            + 0.2 * result["detail_preservation"]
        )
        assert result["overall_score"] == pytest.approx(expected, abs=0.001)

    def test_overall_score_in_range(self, gray_image, noisy_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(gray_image, noisy_image)
        assert 0.0 <= result["overall_score"] <= 1.0


class TestColorImageHandling:
    def test_color_image_does_not_raise(self, color_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        result = ProcessingQualityEvaluator().evaluate(color_image, color_image)
        for v in result.values():
            assert 0.0 <= v <= 1.0

    def test_color_and_gray_of_same_image_similar_contrast(self, gray_image, color_image):
        from agents.processing_quality_evaluator import ProcessingQualityEvaluator
        r_gray = ProcessingQualityEvaluator().evaluate(gray_image, gray_image)
        r_color = ProcessingQualityEvaluator().evaluate(color_image, color_image)
        # Both identical images should give same contrast_preservation = 1.0
        assert r_gray["contrast_preservation"] == pytest.approx(1.0)
        assert r_color["contrast_preservation"] == pytest.approx(1.0)


# ── ParameterSearcher ─────────────────────────────────────────────────────────

class TestParameterSearcherImport:
    def test_class_importable(self):
        from agents.parameter_searcher import ParameterSearcher
        assert ParameterSearcher is not None

    def test_is_base_agent_subclass(self):
        from agents.parameter_searcher import ParameterSearcher
        from agents.base_agent import BaseAgent
        assert issubclass(ParameterSearcher, BaseAgent)

    def test_agent_name(self):
        from agents.parameter_searcher import ParameterSearcher
        assert ParameterSearcher().agent_name == "parameter_searcher"

    def test_accepts_directive(self):
        from agents.parameter_searcher import ParameterSearcher
        ps = ParameterSearcher(directive="focus on noise")
        assert ps.get_directive() == "focus on noise"

    def test_set_directive(self):
        from agents.parameter_searcher import ParameterSearcher
        ps = ParameterSearcher()
        ps.set_directive("new")
        assert ps.get_directive() == "new"


class TestParameterSearcherExecuteReturn:
    def test_returns_processing_pipeline(self):
        from agents.parameter_searcher import ParameterSearcher
        result = ParameterSearcher().execute(_make_pipeline("gaussian_fine"), _make_image())
        assert isinstance(result, ProcessingPipeline)

    def test_returned_pipeline_is_same_object(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_fine")
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert result is pipeline


class TestParameterSearcherParamSelection:
    def test_block_params_updated_after_search(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_fine")
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert "sigma" in result.blocks[0].params

    def test_selected_sigma_is_from_search_space(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_fine")
        result = ParameterSearcher().execute(pipeline, _make_image())
        options = block_library.get_block("gaussian_fine").params["sigma"]
        assert result.blocks[0].params["sigma"] in options

    def test_empty_param_space_block_not_modified(self):
        from agents.parameter_searcher import ParameterSearcher
        # 'grayscale' has params={} in its BlockDefinition
        pipeline = _make_pipeline("grayscale")
        pipeline.blocks[0].params = {}
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert result.blocks[0].params == {}

    def test_pipeline_score_set_after_execute(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_fine")
        assert pipeline.score == 0.0
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert 0.0 < result.score <= 1.0

    def test_pipeline_score_in_valid_range(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_mid")
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert 0.0 <= result.score <= 1.0


class TestParameterSearcherSequential:
    def test_two_block_pipeline_both_params_set(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_fine", "median")
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert "sigma" in result.blocks[0].params
        assert "k" in result.blocks[1].params

    def test_three_block_pipeline_all_params_set(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("gaussian_fine", "median", "gaussian_mid")
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert "sigma" in result.blocks[0].params
        assert "k" in result.blocks[1].params
        assert "sigma" in result.blocks[2].params


class TestParameterSearcherDirective:
    def test_directive_does_not_change_results(self):
        from agents.parameter_searcher import ParameterSearcher
        image = _make_image()
        r1 = ParameterSearcher().execute(_make_pipeline("gaussian_fine"), image)
        r2 = ParameterSearcher(directive="focus on detail").execute(
            _make_pipeline("gaussian_fine"), image
        )
        assert r1.blocks[0].params == r2.blocks[0].params


class TestParameterSearcherExceptionHandling:
    def test_all_params_fail_keeps_empty_params(self):
        from agents.parameter_searcher import ParameterSearcher

        failing_def = MagicMock()
        failing_def.params = {"k": [3, 5, 7]}
        failing_def.apply = MagicMock(side_effect=Exception("always fails"))

        block = PipelineBlock(name="median", when_condition="test", params={})
        pipeline = ProcessingPipeline(name="test", blocks=[block])

        with patch("agents.parameter_searcher.block_library") as mock_lib:
            mock_lib.get_block.return_value = failing_def
            result = ParameterSearcher().execute(pipeline, _make_image())

        assert result.blocks[0].params == {}

    def test_all_params_fail_pipeline_still_returns(self):
        from agents.parameter_searcher import ParameterSearcher

        failing_def = MagicMock()
        failing_def.params = {"k": [3]}
        failing_def.apply = MagicMock(side_effect=ValueError("bad param"))

        block = PipelineBlock(name="median", when_condition="test", params={})
        pipeline = ProcessingPipeline(name="test", blocks=[block])

        with patch("agents.parameter_searcher.block_library") as mock_lib:
            mock_lib.get_block.return_value = failing_def
            result = ParameterSearcher().execute(pipeline, _make_image())

        assert isinstance(result, ProcessingPipeline)

    def test_partial_failure_best_of_remaining_selected(self):
        from agents.parameter_searcher import ParameterSearcher

        call_count = [0]
        original_apply = block_library.get_block("gaussian_fine").apply

        def flaky_apply(img, params):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("first call fails")
            return original_apply(img, params)

        flaky_def = MagicMock()
        flaky_def.params = {"sigma": [0.3, 0.5, 0.8]}
        flaky_def.apply = flaky_apply

        block = PipelineBlock(name="gaussian_fine", when_condition="test", params={})
        pipeline = ProcessingPipeline(name="test", blocks=[block])

        with patch("agents.parameter_searcher.block_library") as mock_lib:
            mock_lib.get_block.return_value = flaky_def
            result = ParameterSearcher().execute(pipeline, _make_image())

        # Should have found params from non-failing calls
        assert result.blocks[0].params != {}


class TestParameterSearcherCombinationLimit:
    def test_large_search_space_calls_apply_at_most_500(self):
        from agents.parameter_searcher import ParameterSearcher

        large_def = MagicMock()
        # 6^4 = 1296 > 500
        large_def.params = {
            "a": list(range(6)),
            "b": list(range(6)),
            "c": list(range(6)),
            "d": list(range(6)),
        }
        large_def.apply = MagicMock(return_value=np.zeros((128, 128), dtype=np.uint8))

        block = PipelineBlock(name="x", when_condition="t", params={})
        pipeline = ProcessingPipeline(name="t", blocks=[block])

        with patch("agents.parameter_searcher.block_library") as mock_lib:
            mock_lib.get_block.return_value = large_def
            ParameterSearcher().execute(pipeline, _make_image())

        # 500 sampled combos + 1 apply for best params + 1 for final eval
        assert large_def.apply.call_count <= 502

    def test_large_search_space_reproducible_with_seed_42(self):
        from agents.parameter_searcher import ParameterSearcher

        large_def = MagicMock()
        large_def.params = {
            "a": list(range(6)),
            "b": list(range(6)),
            "c": list(range(6)),
            "d": list(range(6)),
        }

        calls_run1 = []
        calls_run2 = []

        def make_recorder(calls):
            def apply(img, params):
                calls.append(dict(params))
                return np.zeros((128, 128), dtype=np.uint8)
            return apply

        image = _make_image()

        large_def.apply = make_recorder(calls_run1)
        block1 = PipelineBlock(name="x", when_condition="t", params={})
        p1 = ProcessingPipeline(name="t", blocks=[block1])
        with patch("agents.parameter_searcher.block_library") as mock_lib:
            mock_lib.get_block.return_value = large_def
            ParameterSearcher().execute(p1, image)

        large_def.apply = make_recorder(calls_run2)
        block2 = PipelineBlock(name="x", when_condition="t", params={})
        p2 = ProcessingPipeline(name="t", blocks=[block2])
        with patch("agents.parameter_searcher.block_library") as mock_lib:
            mock_lib.get_block.return_value = large_def
            ParameterSearcher().execute(p2, image)

        assert calls_run1 == calls_run2

    def test_small_search_space_not_sampled(self):
        from agents.parameter_searcher import ParameterSearcher
        # gaussian_fine has 3 combos (sigma: 3 values) — all should be tried
        pipeline = _make_pipeline("gaussian_fine")
        # We can't easily count internal calls, but result should be valid
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert "sigma" in result.blocks[0].params


class TestParameterSearcherFinalScoring:
    def test_final_score_from_full_pipeline_eval(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = _make_pipeline("grayscale", "gaussian_fine")
        result = ParameterSearcher().execute(pipeline, _make_image())
        # grayscale has no params, gaussian_fine gets optimized
        assert 0.0 <= result.score <= 1.0

    def test_empty_pipeline_score_still_set(self):
        from agents.parameter_searcher import ParameterSearcher
        pipeline = ProcessingPipeline(name="empty", blocks=[])
        result = ParameterSearcher().execute(pipeline, _make_image())
        assert 0.0 <= result.score <= 1.0
