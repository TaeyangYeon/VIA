"""Tests for Step 29: Orchestrator Retry Logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from agents.code_validator import ValidationResult
from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    DefectScale,
    EvaluationResult,
    FeedbackAction,
    FailureReason,
    IlluminationType,
    ImageDiagnosis,
    InspectionItem,
    InspectionMode,
    InspectionPlan,
    ItemTestResult,
    JudgementResult,
    NoiseFrequency,
    ProcessingPipeline,
    SpecResult,
    TestMetrics,
)
from agents.orchestrator import Orchestrator


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img() -> np.ndarray:
    return np.zeros((64, 64, 3), dtype=np.uint8)


def _pipeline(name: str = "pipe") -> ProcessingPipeline:
    return ProcessingPipeline(name=name, blocks=[])


def _diagnosis() -> ImageDiagnosis:
    return ImageDiagnosis(
        contrast=0.5, noise_level=0.1, edge_density=0.3, lighting_uniformity=0.8,
        illumination_type=IlluminationType.uniform, noise_frequency=NoiseFrequency.high_freq,
        reflection_level=0.1, texture_complexity=0.2, surface_type="metal",
        defect_scale=DefectScale.macro, blob_feasibility=0.7, blob_count_estimate=3,
        blob_size_variance=0.1, color_discriminability=0.6, dominant_channel_ratio=0.5,
        structural_regularity=0.8, pattern_repetition=0.3, background_uniformity=0.9,
        optimal_color_space="gray", threshold_candidate=128.0, edge_sharpness=0.7,
    )


def _spec(mode: str = "inspection") -> SpecResult:
    return SpecResult(
        mode=InspectionMode(mode),
        goal="detect scratches",
        success_criteria={"accuracy": 0.95, "fp_rate": 0.05, "fn_rate": 0.05},
    )


def _judge(v: float = 0.8, s: float = 0.8, m: float = 0.8) -> JudgementResult:
    return JudgementResult(visibility_score=v, separability_score=s, measurability_score=m)


def _plan() -> InspectionPlan:
    return InspectionPlan(items=[
        InspectionItem(id=1, name="check", purpose="detect", method=AlgorithmCategory.BLOB,
                       success_criteria="accuracy >= 0.9"),
    ])


def _algo(mode: str = "inspection") -> AlgorithmResult:
    if mode == "inspection":
        code = "import cv2\nimport numpy as np\ndef inspect_item(image):\n    return {'result': 'OK'}"
        cat = AlgorithmCategory.BLOB
    else:
        code = "import cv2\nimport numpy as np\ndef align(image):\n    return {'x': 0.0, 'y': 0.0}"
        cat = AlgorithmCategory.TEMPLATE_MATCHING
    return AlgorithmResult(code=code, explanation="ok", category=cat, pipeline=_pipeline())


def _test_results(passed: bool = True) -> list[ItemTestResult]:
    return [ItemTestResult(
        item_id=1, item_name="check", passed=passed,
        metrics=TestMetrics(accuracy=0.95 if passed else 0.3),
    )]


def _eval_result(
    passed: bool = True,
    reason: FailureReason = FailureReason.algorithm_runtime_error,
) -> EvaluationResult:
    return EvaluationResult(
        overall_passed=passed,
        failure_reason=None if passed else reason,
        failed_items=[] if passed else [1],
        analysis="passed" if passed else "failed",
    )


def _feedback_action(
    target: str,
    reason: FailureReason = FailureReason.algorithm_runtime_error,
) -> FeedbackAction:
    return FeedbackAction(
        target_agent=target,
        reason=reason,
        context={"action": "regenerate", "failed_items": [1]},
    )


def _mock_feedback_ctrl(actions=None) -> Mock:
    fc = Mock()
    fc.reset = Mock()
    if actions is None:
        fc.execute = Mock(return_value=_feedback_action("algorithm_coder"))
    elif isinstance(actions, list):
        fc.execute = Mock(side_effect=actions)
    else:
        fc.execute = Mock(return_value=actions)
    return fc


def _mocks(mode: str = "inspection") -> dict:
    spec = Mock()
    spec.execute = AsyncMock(return_value=_spec(mode))
    spec.set_directive = Mock()

    img_agent = Mock()
    img_agent.execute = Mock(return_value=_diagnosis())
    img_agent.set_directive = Mock()

    composer = Mock()
    composer.execute = Mock(return_value=[_pipeline("p1"), _pipeline("p2")])
    composer.set_directive = Mock()

    searcher = Mock()
    searcher.execute = Mock(side_effect=lambda pipeline, image: pipeline)
    searcher.set_directive = Mock()

    judge = Mock()
    judge.execute = AsyncMock(return_value=_judge())
    judge.set_directive = Mock()

    plan_agent = Mock()
    plan_agent.execute = AsyncMock(return_value=_plan())
    plan_agent.set_directive = Mock()

    selector = Mock()
    selector.execute = Mock(return_value=AlgorithmCategory.BLOB)
    selector.set_directive = Mock()

    coder_insp = Mock()
    coder_insp.execute = AsyncMock(return_value=_algo("inspection"))
    coder_insp.set_directive = Mock()

    coder_align = Mock()
    coder_align.execute = AsyncMock(return_value=_algo("align"))
    coder_align.set_directive = Mock()

    validator = Mock()
    validator.validate = Mock(return_value=ValidationResult(is_valid=True))

    test_insp = Mock()
    test_insp.execute = Mock(return_value=_test_results(True))
    test_insp.set_directive = Mock()

    test_aln = Mock()
    test_aln.execute = Mock(return_value=_test_results(True))
    test_aln.set_directive = Mock()

    eval_agent = Mock()
    eval_agent.execute = Mock(return_value=_eval_result(True))
    eval_agent.set_directive = Mock()

    feedback_ctrl = _mock_feedback_ctrl()

    return dict(
        spec_agent=spec, image_analysis_agent=img_agent,
        pipeline_composer=composer, parameter_searcher=searcher,
        vision_judge_agent=judge, inspection_plan_agent=plan_agent,
        algorithm_selector=selector, algorithm_coder_inspection=coder_insp,
        algorithm_coder_align=coder_align, code_validator=validator,
        test_agent_inspection=test_insp, test_agent_align=test_aln,
        evaluation_agent=eval_agent,
        feedback_controller=feedback_ctrl,
    )


def _orc(mode: str = "inspection"):
    m = _mocks(mode)
    return Orchestrator(**m), m


# ── FeedbackController reset ──────────────────────────────────────────────────

class TestFeedbackControllerReset:
    @pytest.mark.anyio
    async def test_reset_called_once_at_start(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [])
        m["feedback_controller"].reset.assert_called_once()

    @pytest.mark.anyio
    async def test_reset_called_before_evaluation(self):
        call_order = []
        orc, m = _orc()
        m["feedback_controller"].reset = Mock(side_effect=lambda: call_order.append("reset"))
        m["evaluation_agent"].execute = Mock(
            side_effect=lambda *a, **kw: call_order.append("eval") or _eval_result(True)
        )
        await orc.execute("detect", [_img()], [])
        assert call_order.index("reset") < call_order.index("eval")

    @pytest.mark.anyio
    async def test_reset_called_once_even_with_retries(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        m["feedback_controller"].reset.assert_called_once()


# ── Iteration history ─────────────────────────────────────────────────────────

class TestIterationHistory:
    @pytest.mark.anyio
    async def test_result_has_iteration_history_key(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert "iteration_history" in result

    @pytest.mark.anyio
    async def test_iteration_history_empty_on_first_pass(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert result["iteration_history"] == []

    @pytest.mark.anyio
    async def test_iteration_history_has_one_entry_after_one_retry(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert len(result["iteration_history"]) == 1

    @pytest.mark.anyio
    async def test_iteration_history_entry_has_required_fields(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        entry = result["iteration_history"][0]
        for field in ("iteration", "failure_reason", "target_agent",
                      "test_results_summary", "judge_result_summary"):
            assert field in entry, f"missing field: {field}"

    @pytest.mark.anyio
    async def test_iteration_history_records_failure_reason(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["iteration_history"][0]["failure_reason"] == "algorithm_runtime_error"

    @pytest.mark.anyio
    async def test_iteration_history_records_target_agent(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["iteration_history"][0]["target_agent"] == "algorithm_coder"

    @pytest.mark.anyio
    async def test_iteration_history_accumulates_multiple_retries(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(False, FailureReason.pipeline_bad_params),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(side_effect=[
            _feedback_action("algorithm_coder"),
            _feedback_action("parameter_searcher"),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert len(result["iteration_history"]) == 2

    @pytest.mark.anyio
    async def test_iteration_history_iteration_numbers_are_sequential(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        nums = [e["iteration"] for e in result["iteration_history"]]
        assert nums == sorted(nums)
        assert len(set(nums)) == len(nums)


# ── Max iteration ─────────────────────────────────────────────────────────────

class TestMaxIteration:
    @pytest.mark.anyio
    async def test_stops_after_default_max_iteration(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [])
        assert m["evaluation_agent"].execute.call_count <= 5

    @pytest.mark.anyio
    async def test_stops_exactly_at_custom_max_iteration(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert m["evaluation_agent"].execute.call_count == 3

    @pytest.mark.anyio
    async def test_status_failed_when_max_iteration_reached(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_iteration_history_length_when_max_reached(self):
        # max=3, all fail: retries triggered for iter 1 and 2 → 2 history entries
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert len(result["iteration_history"]) == 2

    @pytest.mark.anyio
    async def test_max_iteration_1_means_no_retry(self):
        # max=1: only the initial run, no retries
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 1})
        assert m["evaluation_agent"].execute.call_count == 1
        m["feedback_controller"].execute.assert_not_called()


# ── Success on retry ──────────────────────────────────────────────────────────

class TestSuccessOnRetry:
    @pytest.mark.anyio
    async def test_success_on_second_attempt(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_status_success_after_retry(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert orc.get_progress().status == "success"

    @pytest.mark.anyio
    async def test_success_on_third_attempt(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["evaluation_result"].overall_passed is True

    @pytest.mark.anyio
    async def test_evaluation_called_exactly_twice_on_one_retry(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["evaluation_agent"].execute.call_count == 2


# ── current_iteration tracking ────────────────────────────────────────────────

class TestCurrentIterationTracking:
    @pytest.mark.anyio
    async def test_current_iteration_is_1_during_first_evaluation(self):
        iterations_seen = []
        orc, m = _orc()

        def capture(*args, **kwargs):
            iterations_seen.append(orc.get_progress().current_iteration)
            return _eval_result(True)

        m["evaluation_agent"].execute = capture
        await orc.execute("detect", [_img()], [])
        assert iterations_seen[0] == 1

    @pytest.mark.anyio
    async def test_current_iteration_increments_on_retry(self):
        iterations_seen = []
        orc, m = _orc()
        call_count = [0]

        def capture(*args, **kwargs):
            call_count[0] += 1
            iterations_seen.append(orc.get_progress().current_iteration)
            return _eval_result(False) if call_count[0] == 1 else _eval_result(True)

        m["evaluation_agent"].execute = capture
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert iterations_seen == [1, 2]


# ── FeedbackController receives correct arguments ─────────────────────────────

class TestFeedbackControllerArgs:
    @pytest.mark.anyio
    async def test_feedback_controller_called_on_evaluation_failure(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        m["feedback_controller"].execute.assert_called()

    @pytest.mark.anyio
    async def test_feedback_controller_receives_eval_result_as_first_arg(self):
        orc, m = _orc()
        eval_fail = _eval_result(False, FailureReason.algorithm_runtime_error)
        m["evaluation_agent"].execute = Mock(side_effect=[eval_fail, _eval_result(True)])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        first_call = m["feedback_controller"].execute.call_args_list[0]
        passed_eval = first_call.args[0] if first_call.args else first_call.kwargs.get("eval_result")
        assert passed_eval is eval_fail

    @pytest.mark.anyio
    async def test_feedback_controller_receives_judge_result_as_second_arg(self):
        orc, m = _orc()
        judge = _judge(0.9, 0.9, 0.9)
        m["vision_judge_agent"].execute = AsyncMock(return_value=judge)
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        first_call = m["feedback_controller"].execute.call_args_list[0]
        passed_judge = first_call.args[1] if len(first_call.args) > 1 else first_call.kwargs.get("judge_result")
        assert passed_judge is judge

    @pytest.mark.anyio
    async def test_feedback_controller_not_called_on_success(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(return_value=_eval_result(True))
        await orc.execute("detect", [_img()], [])
        m["feedback_controller"].execute.assert_not_called()


# ── Retry routing: restart points ─────────────────────────────────────────────

class TestRetryRoutingAlgorithmCoder:
    @pytest.mark.anyio
    async def test_reruns_coder_inspection(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_coder_inspection"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_skips_pipeline_composer(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_skips_algorithm_selector(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_selector"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_skips_inspection_plan(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["inspection_plan_agent"].execute.call_count == 1


class TestRetryRoutingAlgorithmSelector:
    @pytest.mark.anyio
    async def test_reruns_selector(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_wrong_category),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_selector", FailureReason.algorithm_wrong_category)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_selector"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_reruns_coder_after_selector(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_wrong_category),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_selector", FailureReason.algorithm_wrong_category)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_coder_inspection"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_skips_pipeline_composer(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_wrong_category),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_selector", FailureReason.algorithm_wrong_category)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_skips_inspection_plan(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_wrong_category),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_selector", FailureReason.algorithm_wrong_category)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["inspection_plan_agent"].execute.call_count == 1


class TestRetryRoutingInspectionPlan:
    @pytest.mark.anyio
    async def test_reruns_inspection_plan(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.inspection_plan_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("inspection_plan", FailureReason.inspection_plan_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["inspection_plan_agent"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_reruns_selector_and_coder_after_plan(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.inspection_plan_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("inspection_plan", FailureReason.inspection_plan_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_selector"].execute.call_count == 2
        assert m["algorithm_coder_inspection"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_skips_pipeline_composer(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.inspection_plan_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("inspection_plan", FailureReason.inspection_plan_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 1


class TestRetryRoutingPipelineComposer:
    @pytest.mark.anyio
    async def test_reruns_composer(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("pipeline_composer", FailureReason.pipeline_bad_fit)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_skips_spec_agent(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("pipeline_composer", FailureReason.pipeline_bad_fit)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["spec_agent"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_skips_image_analysis(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("pipeline_composer", FailureReason.pipeline_bad_fit)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["image_analysis_agent"].execute.call_count == 1


class TestRetryRoutingParameterSearcher:
    @pytest.mark.anyio
    async def test_reruns_parameter_searcher(self):
        orc, m = _orc("inspection")
        # Initial: 2 candidates → searcher called 2 times. On retry: 2 more → total 4.
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_params),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("parameter_searcher", FailureReason.pipeline_bad_params)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["parameter_searcher"].execute.call_count > 2

    @pytest.mark.anyio
    async def test_skips_pipeline_composer(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_params),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("parameter_searcher", FailureReason.pipeline_bad_params)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 1


class TestRetryRoutingSpecAgent:
    @pytest.mark.anyio
    async def test_reruns_spec_agent(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.spec_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("spec_agent", FailureReason.spec_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["spec_agent"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_reruns_composer_after_spec(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.spec_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("spec_agent", FailureReason.spec_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_skips_image_analysis(self):
        orc, m = _orc("inspection")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.spec_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("spec_agent", FailureReason.spec_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        # image_analysis is NEVER re-run regardless of restart point
        assert m["image_analysis_agent"].execute.call_count == 1


# ── Align mode retry ──────────────────────────────────────────────────────────

class TestAlignModeRetry:
    @pytest.mark.anyio
    async def test_algorithm_coder_restart_reruns_coder_align(self):
        orc, m = _orc("align")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        assert m["algorithm_coder_align"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_pipeline_composer_restart_in_align(self):
        orc, m = _orc("align")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("pipeline_composer", FailureReason.pipeline_bad_fit)
        )
        await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        assert m["pipeline_composer"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_align_retry_does_not_call_inspection_agents(self):
        orc, m = _orc("align")
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("algorithm_coder")
        )
        await orc.execute("align", [_img()], [], config={"max_iteration": 5})
        m["inspection_plan_agent"].execute.assert_not_called()
        m["algorithm_selector"].execute.assert_not_called()


# ── Image analysis never re-run ───────────────────────────────────────────────

class TestImageAnalysisNotRerun:
    @pytest.mark.anyio
    async def test_image_analysis_called_once_across_multiple_retries(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.pipeline_bad_fit),
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(side_effect=[
            _feedback_action("pipeline_composer"),
            _feedback_action("algorithm_coder"),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["image_analysis_agent"].execute.call_count == 1

    @pytest.mark.anyio
    async def test_image_analysis_called_once_even_on_spec_restart(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.spec_issue),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(
            return_value=_feedback_action("spec_agent", FailureReason.spec_issue)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert m["image_analysis_agent"].execute.call_count == 1


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    @pytest.mark.anyio
    async def test_feedback_returns_none_sets_status_failed(self):
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        m["feedback_controller"].execute = Mock(return_value=None)
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result is not None
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_no_feedback_controller_still_sets_failed_on_eval_failure(self):
        """Orchestrator without feedback_controller behaves like Step 28."""
        m = _mocks()
        del m["feedback_controller"]
        orc = Orchestrator(**m)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [])
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_no_feedback_controller_no_retry(self):
        """Without feedback_controller, evaluation is called only once even on failure."""
        m = _mocks()
        del m["feedback_controller"]
        orc = Orchestrator(**m)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [])
        assert m["evaluation_agent"].execute.call_count == 1
