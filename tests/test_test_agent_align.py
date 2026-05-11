"""Tests for TestAgentAlign — synchronous align() execution and coordinate metrics."""
import inspect
import math

import numpy as np
import pytest

from agents.base_agent import BaseAgent
from agents.models import ItemTestResult, TestMetrics
from agents.test_agent_align import TestAgentAlign
from backend.services.logger import via_logger


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img() -> np.ndarray:
    return np.zeros((50, 50, 3), dtype=np.uint8)


def _align_code(x: float = 0.0, y: float = 0.0, confidence: float = 0.9) -> str:
    return (
        f"def align(image):\n"
        f"    return {{'x': {x}, 'y': {y}, 'confidence': {confidence}, 'method_used': 'template'}}"
    )


def _err_code() -> str:
    return "def align(image):\n    raise RuntimeError('test error')"


def _filename(x: float, y: float, idx: int = 0) -> str:
    return f"X_{x}_Y_{y}_{idx}.png"


def _run(
    code: str,
    images: list[tuple[np.ndarray, str]],
    success_criteria: list[str] | None = None,
    agent: TestAgentAlign | None = None,
) -> list[ItemTestResult]:
    if agent is None:
        agent = TestAgentAlign()
    return agent.execute(code=code, test_images=images, success_criteria=success_criteria)


# ── 1. Class Structure ────────────────────────────────────────────────────────

class TestClassStructure:
    def test_inherits_base_agent(self):
        assert issubclass(TestAgentAlign, BaseAgent)

    def test_agent_name(self):
        assert TestAgentAlign().agent_name == "test_agent_align"

    def test_execute_is_synchronous(self):
        assert not inspect.iscoroutinefunction(TestAgentAlign().execute)

    def test_directive_none_by_default(self):
        assert TestAgentAlign().get_directive() is None

    def test_directive_in_constructor(self):
        assert TestAgentAlign(directive="d").get_directive() == "d"

    def test_set_directive(self):
        agent = TestAgentAlign()
        agent.set_directive("new")
        assert agent.get_directive() == "new"


# ── 2. Return Type ────────────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_list(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert isinstance(result, list)

    def test_returns_single_element(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert len(result) == 1

    def test_returns_item_test_result_instance(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert isinstance(result[0], ItemTestResult)

    def test_item_id_is_zero(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert result[0].item_id == 0

    def test_item_name_is_align(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert result[0].item_name == "align"

    def test_metrics_is_test_metrics_instance(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert isinstance(result[0].metrics, TestMetrics)


# ── 3. Function Extraction ────────────────────────────────────────────────────

class TestFunctionExtraction:
    def test_valid_align_function_extracted(self):
        result = _run(_align_code(0.0, 0.0), [(_img(), _filename(0.0, 0.0))])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_invalid_syntax_returns_failed_result(self):
        result = _run("this is ??? not valid python", [(_img(), _filename(10.0, 20.0))])
        assert result[0].passed is False

    def test_invalid_syntax_error_in_details(self):
        result = _run("this is ??? not valid python", [(_img(), _filename(10.0, 20.0))])
        assert "error" in result[0].details.lower()

    def test_missing_align_function_returns_failed(self):
        code = "def other_function(image):\n    return {'x': 0.0, 'y': 0.0}"
        result = _run(code, [(_img(), _filename(10.0, 20.0))])
        assert result[0].passed is False

    def test_missing_align_function_error_in_details(self):
        code = "def other_function(image):\n    return {'x': 0.0, 'y': 0.0}"
        result = _run(code, [(_img(), _filename(10.0, 20.0))])
        assert "error" in result[0].details.lower()

    def test_empty_code_returns_failed(self):
        result = _run("", [(_img(), _filename(10.0, 20.0))])
        assert result[0].passed is False

    def test_np_available_in_exec_namespace(self):
        code = (
            "import numpy as np\n"
            "def align(image):\n"
            "    arr = np.array([1.0, 2.0])\n"
            "    return {'x': float(arr[0]), 'y': float(arr[1]), 'confidence': 0.9, 'method_used': 'np'}"
        )
        result = _run(code, [(_img(), _filename(1.0, 2.0))])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_cv2_available_in_exec_namespace(self):
        code = (
            "def align(image):\n"
            "    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)\n"
            "    return {'x': 0.0, 'y': 0.0, 'confidence': 0.9, 'method_used': 'cv2'}"
        )
        result = _run(code, [(_img(), _filename(0.0, 0.0))])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)


# ── 4. Ground Truth Filename Parsing ─────────────────────────────────────────

class TestGroundTruthParsing:
    def test_float_coordinates_parsed(self):
        result = _run(_align_code(123.4, 567.8), [(_img(), "X_123.4_Y_567.8_0.png")])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_integer_coordinates_parsed(self):
        result = _run(_align_code(100.0, 200.0), [(_img(), "X_100_Y_200_1.png")])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_zero_coordinates_parsed(self):
        result = _run(_align_code(0.0, 0.0), [(_img(), "X_0_Y_0_0.png")])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_invalid_filename_skipped(self):
        # Only invalid filename → no valid images → coord_error=0.0 or defined behavior
        result = _run(_align_code(), [(_img(), "unknown_sample.png")])
        assert len(result) == 1

    def test_invalid_filename_does_not_crash(self):
        result = _run(_align_code(), [(_img(), "no_coords.png")])
        assert result[0].item_id == 0

    def test_mixed_valid_invalid_filenames(self):
        images = [
            (_img(), "X_10.0_Y_20.0_0.png"),
            (_img(), "invalid_filename.png"),
            (_img(), "X_10.0_Y_20.0_1.png"),
        ]
        result = _run(_align_code(10.0, 20.0), images)
        # Only 2 valid → coord_error should reflect the 2 valid images
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_large_index_in_filename(self):
        result = _run(_align_code(50.0, 75.5), [(_img(), "X_50.0_Y_75.5_999.png")])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)


# ── 5. Metrics Computation ────────────────────────────────────────────────────

class TestMetricsComputation:
    def test_perfect_alignment_coord_error_zero(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_align_code(10.0, 20.0), images)
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_coord_error_euclidean_distance(self):
        # pred=(0,0), gt=(3,4) → distance=5.0
        images = [(_img(), _filename(3.0, 4.0))]
        result = _run(_align_code(0.0, 0.0), images)
        assert result[0].metrics.coord_error == pytest.approx(5.0, abs=1e-6)

    def test_coord_error_average_across_images(self):
        # pred=(0,0), gt1=(3,4)→5.0, gt2=(0,0)→0.0 → avg=2.5
        code = _align_code(0.0, 0.0)
        images = [(_img(), _filename(3.0, 4.0)), (_img(), _filename(0.0, 0.0, idx=1))]
        result = _run(code, images)
        assert result[0].metrics.coord_error == pytest.approx(2.5, abs=1e-6)

    def test_success_rate_all_within_threshold(self):
        # All errors < 2.0 → success_rate=1.0
        images = [(_img(), _filename(10.0, 20.0)), (_img(), _filename(10.0, 20.0, idx=1))]
        result = _run(_align_code(10.0, 20.0), images)
        assert result[0].metrics.success_rate == pytest.approx(1.0)

    def test_success_rate_none_within_threshold(self):
        # Error=5.0 > 2.0 → success_rate=0.0
        images = [(_img(), _filename(3.0, 4.0))]
        result = _run(_align_code(0.0, 0.0), images)
        assert result[0].metrics.success_rate == pytest.approx(0.0)

    def test_success_rate_partial(self):
        # 1 perfect (error=0), 1 bad (error=5): 1/2=0.5
        code = _align_code(0.0, 0.0)
        images = [(_img(), _filename(0.0, 0.0)), (_img(), _filename(3.0, 4.0, idx=1))]
        result = _run(code, images)
        assert result[0].metrics.success_rate == pytest.approx(0.5)

    def test_accuracy_is_zero(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert result[0].metrics.accuracy == 0.0

    def test_fp_rate_is_zero(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert result[0].metrics.fp_rate == 0.0

    def test_fn_rate_is_zero(self):
        result = _run(_align_code(), [(_img(), _filename(10.0, 20.0))])
        assert result[0].metrics.fn_rate == 0.0

    def test_coord_error_nonnegative(self):
        result = _run(_align_code(10.0, 20.0), [(_img(), _filename(10.0, 20.0))])
        assert result[0].metrics.coord_error >= 0.0

    def test_success_rate_between_zero_and_one(self):
        result = _run(_align_code(10.0, 20.0), [(_img(), _filename(10.0, 20.0))])
        assert 0.0 <= result[0].metrics.success_rate <= 1.0

    def test_exception_in_align_treated_as_large_error(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_err_code(), images)
        assert result[0].metrics.coord_error > 100.0

    def test_exception_success_rate_zero(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_err_code(), images)
        assert result[0].metrics.success_rate == pytest.approx(0.0)

    def test_single_image_perfect(self):
        result = _run(_align_code(5.5, 7.7), [(_img(), _filename(5.5, 7.7))])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)
        assert result[0].metrics.success_rate == pytest.approx(1.0)


# ── 6. Success Criteria Evaluation ───────────────────────────────────────────

class TestSuccessCriteriaEvaluation:
    def test_default_criteria_passes_perfect_alignment(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_align_code(10.0, 20.0), images)
        assert result[0].passed is True

    def test_default_criteria_fails_large_error(self):
        # error=5.0, default coord_error <= 2.0 → fails
        images = [(_img(), _filename(3.0, 4.0))]
        result = _run(_align_code(0.0, 0.0), images)
        assert result[0].passed is False

    def test_custom_coord_error_criteria_passes(self):
        images = [(_img(), _filename(3.0, 4.0))]
        # error=5.0, criteria allows <= 10.0
        result = _run(_align_code(0.0, 0.0), images, success_criteria=["coord_error <= 10.0"])
        assert result[0].passed is True

    def test_custom_coord_error_criteria_fails(self):
        images = [(_img(), _filename(3.0, 4.0))]
        # error=5.0, criteria requires <= 1.0
        result = _run(_align_code(0.0, 0.0), images, success_criteria=["coord_error <= 1.0"])
        assert result[0].passed is False

    def test_custom_success_rate_criteria_passes(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_align_code(10.0, 20.0), images, success_criteria=["success_rate >= 0.5"])
        assert result[0].passed is True

    def test_custom_success_rate_criteria_fails(self):
        # success_rate=0.0 (error=5.0 > 2.0), requires >= 0.9
        images = [(_img(), _filename(3.0, 4.0))]
        result = _run(_align_code(0.0, 0.0), images, success_criteria=["success_rate >= 0.9"])
        assert result[0].passed is False

    def test_multiple_criteria_all_must_pass(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(
            _align_code(10.0, 20.0),
            images,
            success_criteria=["coord_error <= 2.0", "success_rate >= 0.9"],
        )
        assert result[0].passed is True

    def test_multiple_criteria_one_fails(self):
        # error=5.0: coord_error <= 2.0 fails even if success_rate criteria would pass at >= 0.0
        images = [(_img(), _filename(3.0, 4.0))]
        result = _run(
            _align_code(0.0, 0.0),
            images,
            success_criteria=["coord_error <= 2.0", "success_rate >= 0.0"],
        )
        assert result[0].passed is False

    def test_empty_criteria_list_uses_defaults(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_align_code(10.0, 20.0), images, success_criteria=[])
        assert result[0].passed is True

    def test_none_criteria_uses_defaults(self):
        images = [(_img(), _filename(10.0, 20.0))]
        result = _run(_align_code(10.0, 20.0), images, success_criteria=None)
        assert result[0].passed is True


# ── 7. Edge Cases ─────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_image_list_returns_single_result(self):
        result = _run(_align_code(), [])
        assert len(result) == 1
        assert result[0].item_id == 0

    def test_empty_image_list_coord_error_zero(self):
        result = _run(_align_code(), [])
        assert result[0].metrics.coord_error == pytest.approx(0.0, abs=1e-6)

    def test_empty_image_list_success_rate_zero(self):
        result = _run(_align_code(), [])
        assert result[0].metrics.success_rate == pytest.approx(0.0)

    def test_empty_image_list_not_passed(self):
        result = _run(_align_code(), [])
        assert result[0].passed is False

    def test_no_valid_gt_images_all_skipped(self):
        # All filenames invalid → no valid GT images → similar to empty
        images = [(_img(), "bad.png"), (_img(), "also_bad.jpg")]
        result = _run(_align_code(), images)
        assert len(result) == 1

    def test_align_exception_partial_images(self):
        # 1 image where align throws, 1 valid → avg error uses large error + real error
        code = _err_code()
        images = [(_img(), _filename(0.0, 0.0))]
        result = _run(code, images)
        assert result[0].metrics.coord_error >= 100.0

    def test_multiple_images_exception_each_counted(self):
        images = [(_img(), _filename(0.0, 0.0, i)) for i in range(3)]
        result = _run(_err_code(), images)
        assert result[0].metrics.success_rate == pytest.approx(0.0)

    def test_result_always_single_element(self):
        # Multiple calls, always single element
        for n in range(1, 4):
            images = [(_img(), _filename(float(i), float(i), i)) for i in range(n)]
            result = _run(_align_code(0.0, 0.0), images)
            assert len(result) == 1


# ── 8. Directive Support ──────────────────────────────────────────────────────

class TestDirectiveSupport:
    def test_directive_does_not_change_results(self):
        images = [(_img(), _filename(10.0, 20.0))]
        r_no = _run(_align_code(10.0, 20.0), images)
        r_dir = _run(_align_code(10.0, 20.0), images, agent=TestAgentAlign(directive="정밀 정렬"))
        assert r_no[0].metrics.coord_error == pytest.approx(r_dir[0].metrics.coord_error)

    def test_directive_is_logged(self):
        via_logger.clear()
        agent = TestAgentAlign(directive="테스트 지시")
        agent.execute(
            code=_align_code(10.0, 20.0),
            test_images=[(_img(), _filename(10.0, 20.0))],
        )
        logs = via_logger.get_logs(agent="test_agent_align")
        assert any(
            "테스트 지시" in str(log.get("message", "")) or
            "테스트 지시" in str(log.get("details", ""))
            for log in logs
        )

    def test_no_directive_no_directive_log(self):
        via_logger.clear()
        agent = TestAgentAlign()
        agent.execute(
            code=_align_code(),
            test_images=[(_img(), _filename(0.0, 0.0))],
        )
        logs = via_logger.get_logs(agent="test_agent_align")
        directive_logs = [l for l in logs if "Directive" in str(l.get("message", ""))]
        assert len(directive_logs) == 0


# ── 9. Logging Verification ───────────────────────────────────────────────────

class TestLoggingVerification:
    def test_info_logged_on_start(self):
        via_logger.clear()
        _run(_align_code(), [(_img(), _filename(0.0, 0.0))])
        logs = via_logger.get_logs(agent="test_agent_align", level="INFO")
        assert len(logs) > 0

    def test_info_logged_on_completion(self):
        via_logger.clear()
        _run(_align_code(10.0, 20.0), [(_img(), _filename(10.0, 20.0))])
        logs = via_logger.get_logs(agent="test_agent_align", level="INFO")
        assert len(logs) >= 2

    def test_warning_logged_on_invalid_filename(self):
        via_logger.clear()
        _run(_align_code(), [(_img(), "invalid_no_coords.png")])
        logs = via_logger.get_logs(agent="test_agent_align")
        assert any(l["level"] == "WARNING" for l in logs)

    def test_warning_logged_on_extraction_failure(self):
        via_logger.clear()
        _run("this is ??? not valid python", [(_img(), _filename(0.0, 0.0))])
        logs = via_logger.get_logs(agent="test_agent_align")
        assert any(l["level"] == "WARNING" for l in logs)

    def test_log_agent_name_correct(self):
        via_logger.clear()
        _run(_align_code(), [(_img(), _filename(0.0, 0.0))])
        logs = via_logger.get_logs(agent="test_agent_align")
        assert len(logs) > 0
        assert all(l["agent"] == "test_agent_align" for l in logs)
