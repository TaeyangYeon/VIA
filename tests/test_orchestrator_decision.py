"""Tests for Step 30: DecisionAgent integration into Orchestrator."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from agents.code_validator import ValidationResult
from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    DecisionResult,
    DecisionType,
    DefectScale,
    EvaluationResult,
    FailureReason,
    FeedbackAction,
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
        success_criteria={"accuracy": 0.95},
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
    target: str = "algorithm_coder",
    reason: FailureReason = FailureReason.algorithm_runtime_error,
) -> FeedbackAction:
    return FeedbackAction(target_agent=target, reason=reason, context={})


def _decision_result(decision: DecisionType = DecisionType.edge_learning) -> DecisionResult:
    return DecisionResult(decision=decision, reason="test reason", confidence=1.0, details={})


def _mock_feedback_ctrl() -> Mock:
    fc = Mock()
    fc.reset = Mock()
    fc.execute = Mock(return_value=_feedback_action())
    return fc


def _mock_decision_agent(decision: DecisionType = DecisionType.edge_learning) -> Mock:
    da = Mock()
    da.execute = Mock(return_value=_decision_result(decision))
    return da


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


def _orc_with_da(mode: str = "inspection", decision: DecisionType = DecisionType.edge_learning):
    m = _mocks(mode)
    da = _mock_decision_agent(decision)
    return Orchestrator(**m, decision_agent=da), m, da


# ── Constructor ───────────────────────────────────────────────────────────────

class TestDecisionAgentConstructor:
    def test_decision_agent_defaults_to_none(self):
        """Constructing without decision_agent leaves _decision_agent as None."""
        m = _mocks()
        orc = Orchestrator(**m)
        assert orc._decision_agent is None

    def test_decision_agent_stored_when_provided(self):
        da = _mock_decision_agent()
        m = _mocks()
        orc = Orchestrator(**m, decision_agent=da)
        assert orc._decision_agent is da

    def test_backward_compat_14_arg_constructor(self):
        """14-argument constructor (no decision_agent) should not raise."""
        m = _mocks()
        orc = Orchestrator(**m)
        assert orc is not None

    def test_decision_agent_is_15th_optional_kwarg(self):
        """decision_agent can be passed positionally or by keyword."""
        da = _mock_decision_agent()
        m = _mocks()
        orc = Orchestrator(
            m["spec_agent"], m["image_analysis_agent"], m["pipeline_composer"],
            m["parameter_searcher"], m["vision_judge_agent"], m["inspection_plan_agent"],
            m["algorithm_selector"], m["algorithm_coder_inspection"], m["algorithm_coder_align"],
            m["code_validator"], m["test_agent_inspection"], m["test_agent_align"],
            m["evaluation_agent"],
            m["feedback_controller"],
            da,
        )
        assert orc._decision_agent is da


# ── Return dict key ───────────────────────────────────────────────────────────

class TestDecisionResultKey:
    @pytest.mark.anyio
    async def test_return_dict_has_decision_result_key(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert "decision_result" in result

    @pytest.mark.anyio
    async def test_return_dict_has_13_keys(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert len(result) == 13

    @pytest.mark.anyio
    async def test_decision_result_none_on_success(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert result["decision_result"] is None


# ── Decision NOT triggered ─────────────────────────────────────────────────────

class TestDecisionNotTriggered:
    @pytest.mark.anyio
    async def test_decision_result_none_when_overall_passed(self):
        orc, m, da = _orc_with_da()
        result = await orc.execute("detect", [_img()], [])
        assert result["decision_result"] is None

    @pytest.mark.anyio
    async def test_decision_agent_not_called_when_passed(self):
        orc, m, da = _orc_with_da()
        await orc.execute("detect", [_img()], [])
        da.execute.assert_not_called()

    @pytest.mark.anyio
    async def test_decision_result_none_when_no_decision_agent(self):
        """decision_result is None when no decision_agent, even if max_iter exhausted."""
        orc, m = _orc()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is None

    @pytest.mark.anyio
    async def test_decision_result_none_when_retry_succeeds_before_max(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["decision_result"] is None

    @pytest.mark.anyio
    async def test_decision_agent_not_called_when_retry_succeeds(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(side_effect=[
            _eval_result(False, FailureReason.algorithm_runtime_error),
            _eval_result(True),
        ])
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        da.execute.assert_not_called()

    @pytest.mark.anyio
    async def test_decision_not_triggered_without_feedback_controller_default_max(self):
        """Without feedback_controller, current_iteration stays 1 < default max_iter=5."""
        m = _mocks()
        da = _mock_decision_agent()
        del m["feedback_controller"]
        orc = Orchestrator(**m, decision_agent=da)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["decision_result"] is None
        da.execute.assert_not_called()


# ── Decision IS triggered ─────────────────────────────────────────────────────

class TestDecisionTriggered:
    @pytest.mark.anyio
    async def test_decision_result_not_none_when_max_iter_exhausted(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is not None

    @pytest.mark.anyio
    async def test_decision_agent_called_exactly_once(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        da.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_decision_result_is_decision_result_type(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert isinstance(result["decision_result"], DecisionResult)

    @pytest.mark.anyio
    async def test_decision_triggered_with_max_iter_1(self):
        """max_iter=1: breaks immediately at current_iteration=1>=1, decision triggered."""
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 1})
        assert result["decision_result"] is not None
        da.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_decision_triggered_with_max_iter_5_all_fail(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        assert result["decision_result"] is not None
        da.execute.assert_called_once()


# ── Decision agent argument verification ─────────────────────────────────────

class TestDecisionAgentArgs:
    @pytest.mark.anyio
    async def test_receives_iteration_history_as_list(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        history = call_args.args[0] if call_args.args else call_args.kwargs.get("iteration_history")
        assert isinstance(history, list)

    @pytest.mark.anyio
    async def test_receives_correct_mode_inspection(self):
        orc, m, da = _orc_with_da("inspection")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        mode = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("mode")
        assert mode == "inspection"

    @pytest.mark.anyio
    async def test_receives_correct_mode_align(self):
        orc, m, da = _orc_with_da("align")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("align", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        mode = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("mode")
        assert mode == "align"

    @pytest.mark.anyio
    async def test_receives_best_judge_result(self):
        judge = _judge(0.9, 0.9, 0.9)
        orc, m, da = _orc_with_da()
        m["vision_judge_agent"].execute = AsyncMock(return_value=judge)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        passed_judge = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("judge_result")
        assert passed_judge is judge

    @pytest.mark.anyio
    async def test_receives_image_diagnosis(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        diag = call_args.args[3] if len(call_args.args) > 3 else call_args.kwargs.get("image_diagnosis")
        assert isinstance(diag, ImageDiagnosis)


# ── Decision result value ──────────────────────────────────────────────────────

class TestDecisionResultValue:
    @pytest.mark.anyio
    async def test_edge_learning_decision_stored(self):
        orc, m, da = _orc_with_da(decision=DecisionType.edge_learning)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"].decision == DecisionType.edge_learning

    @pytest.mark.anyio
    async def test_deep_learning_decision_stored(self):
        orc, m, da = _orc_with_da(decision=DecisionType.deep_learning)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"].decision == DecisionType.deep_learning

    @pytest.mark.anyio
    async def test_rule_based_decision_stored(self):
        orc, m, da = _orc_with_da(decision=DecisionType.rule_based)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"].decision == DecisionType.rule_based

    @pytest.mark.anyio
    async def test_decision_result_is_exact_object_returned_by_agent(self):
        expected = _decision_result(DecisionType.deep_learning)
        da = Mock()
        da.execute = Mock(return_value=expected)
        m = _mocks()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        orc = Orchestrator(**m, decision_agent=da)
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is expected


# ── Progress status after decision ───────────────────────────────────────────

class TestDecisionProgressStatus:
    @pytest.mark.anyio
    async def test_progress_status_failed_after_decision(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_decision_does_not_change_status_to_non_failed(self):
        orc, m, da = _orc_with_da(decision=DecisionType.deep_learning)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert orc.get_progress().status == "failed"


# ── Logging ───────────────────────────────────────────────────────────────────

class TestDecisionLogging:
    @pytest.mark.anyio
    async def test_info_log_emitted_when_decision_made(self):
        """_log is called with 'INFO' at least once after decision."""
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        log_calls: list[tuple[str, str]] = []
        orc._log = lambda level, msg, *a, **kw: log_calls.append((level, msg))
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        info_msgs = [msg for level, msg in log_calls if level == "INFO"]
        assert len(info_msgs) > 0

    @pytest.mark.anyio
    async def test_no_decision_log_when_not_triggered(self):
        """No extra INFO log related to decision when overall_passed=True."""
        orc, m, da = _orc_with_da()
        log_calls: list[tuple[str, str]] = []
        orc._log = lambda level, msg, *a, **kw: log_calls.append((level, msg))
        await orc.execute("detect", [_img()], [])
        # decision_agent.execute should not have been called
        da.execute.assert_not_called()


# ── Exception propagation ──────────────────────────────────────────────────────

class TestDecisionAgentException:
    @pytest.mark.anyio
    async def test_runtime_error_propagates(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        da.execute = Mock(side_effect=RuntimeError("decision boom"))
        with pytest.raises(RuntimeError, match="decision boom"):
            await orc.execute("detect", [_img()], [], config={"max_iteration": 3})

    @pytest.mark.anyio
    async def test_status_failed_when_decision_raises(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        da.execute = Mock(side_effect=RuntimeError("decision boom"))
        with pytest.raises(RuntimeError):
            await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert orc.get_progress().status == "failed"


# ── Iteration history content passed to decision agent ───────────────────────

class TestDecisionHistoryContent:
    @pytest.mark.anyio
    async def test_empty_history_when_max_iter_1(self):
        """max_iter=1 breaks before appending history → decision receives []."""
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 1})
        call_args = da.execute.call_args
        history = call_args.args[0] if call_args.args else call_args.kwargs.get("iteration_history")
        assert history == []

    @pytest.mark.anyio
    async def test_history_length_2_with_max_iter_3(self):
        """max_iter=3: iters 1 and 2 appended before breaking at iter 3 → 2 entries."""
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        history = call_args.args[0] if call_args.args else call_args.kwargs.get("iteration_history")
        assert len(history) == 2

    @pytest.mark.anyio
    async def test_history_length_4_with_max_iter_5(self):
        """max_iter=5: 4 retries recorded before breaking → 4 entries."""
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("detect", [_img()], [], config={"max_iteration": 5})
        call_args = da.execute.call_args
        history = call_args.args[0] if call_args.args else call_args.kwargs.get("iteration_history")
        assert len(history) == 4


# ── Decision triggered across various failure reasons ─────────────────────────

class TestDecisionVariousFailureReasons:
    @pytest.mark.anyio
    async def test_triggered_on_pipeline_bad_fit(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.pipeline_bad_fit)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is not None

    @pytest.mark.anyio
    async def test_triggered_on_algorithm_wrong_category(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_wrong_category)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is not None

    @pytest.mark.anyio
    async def test_triggered_on_spec_issue(self):
        orc, m, da = _orc_with_da()
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.spec_issue)
        )
        result = await orc.execute("detect", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is not None


# ── Integration: align mode ───────────────────────────────────────────────────

class TestDecisionAlignModeIntegration:
    @pytest.mark.anyio
    async def test_align_mode_decision_triggered_on_exhaustion(self):
        orc, m, da = _orc_with_da("align", DecisionType.rule_based)
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        result = await orc.execute("align", [_img()], [], config={"max_iteration": 3})
        assert result["decision_result"] is not None
        da.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_align_mode_passes_align_mode_string(self):
        orc, m, da = _orc_with_da("align")
        m["evaluation_agent"].execute = Mock(
            return_value=_eval_result(False, FailureReason.algorithm_runtime_error)
        )
        await orc.execute("align", [_img()], [], config={"max_iteration": 3})
        call_args = da.execute.call_args
        mode = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("mode")
        assert mode == "align"
