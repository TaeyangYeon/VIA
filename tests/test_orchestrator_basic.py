"""Tests for Step 28: Orchestrator Basic Pipeline."""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from agents.base_agent import BaseAgent
from agents.code_validator import ValidationResult
from agents.models import (
    AgentDirectives,
    AlgorithmCategory,
    AlgorithmResult,
    DefectScale,
    EvaluationResult,
    ExecutionProgress,
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


def _eval_result(passed: bool = True) -> EvaluationResult:
    return EvaluationResult(
        overall_passed=passed,
        failure_reason=None if passed else FailureReason.algorithm_runtime_error,
        failed_items=[] if passed else [1],
        analysis="passed" if passed else "failed",
    )


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

    return dict(
        spec_agent=spec, image_analysis_agent=img_agent,
        pipeline_composer=composer, parameter_searcher=searcher,
        vision_judge_agent=judge, inspection_plan_agent=plan_agent,
        algorithm_selector=selector, algorithm_coder_inspection=coder_insp,
        algorithm_coder_align=coder_align, code_validator=validator,
        test_agent_inspection=test_insp, test_agent_align=test_aln,
        evaluation_agent=eval_agent,
    )


def _orc(mode: str = "inspection"):
    m = _mocks(mode)
    return Orchestrator(**m), m


# ── Class structure ───────────────────────────────────────────────────────────

class TestOrchestratorClass:
    def test_inherits_base_agent(self):
        orc, _ = _orc()
        assert isinstance(orc, BaseAgent)

    def test_agent_name_is_orchestrator(self):
        orc, _ = _orc()
        assert orc.agent_name == "orchestrator"

    def test_default_directive_is_none(self):
        orc, _ = _orc()
        assert orc.get_directive() is None

    def test_set_directive_works(self):
        orc, _ = _orc()
        orc.set_directive("test")
        assert orc.get_directive() == "test"

    def test_execute_is_async(self):
        orc, _ = _orc()
        assert inspect.iscoroutinefunction(orc.execute)

    def test_initial_progress_status_is_idle(self):
        orc, _ = _orc()
        assert orc.get_progress().status == "idle"

    def test_get_progress_returns_execution_progress(self):
        orc, _ = _orc()
        assert isinstance(orc.get_progress(), ExecutionProgress)

    def test_constructor_accepts_all_agents(self):
        m = _mocks()
        orc = Orchestrator(**m)
        assert orc is not None


# ── Directive distribution ───────────────────────────────────────────────────

class TestDirectiveDistribution:
    @pytest.mark.anyio
    async def test_spec_directive_distributed(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [], directives=AgentDirectives(spec="strict"))
        m["spec_agent"].set_directive.assert_called_with("strict")

    @pytest.mark.anyio
    async def test_image_analysis_directive_distributed(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [], directives=AgentDirectives(image_analysis="edges"))
        m["image_analysis_agent"].set_directive.assert_called_with("edges")

    @pytest.mark.anyio
    async def test_pipeline_composer_directive_distributed(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [], directives=AgentDirectives(pipeline_composer="blur"))
        m["pipeline_composer"].set_directive.assert_called_with("blur")

    @pytest.mark.anyio
    async def test_vision_judge_directive_distributed(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [], directives=AgentDirectives(vision_judge="strict"))
        m["vision_judge_agent"].set_directive.assert_called_with("strict")

    @pytest.mark.anyio
    async def test_algorithm_coder_directive_distributed_inspection(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [], directives=AgentDirectives(algorithm_coder="blob"))
        m["algorithm_coder_inspection"].set_directive.assert_called_with("blob")

    @pytest.mark.anyio
    async def test_algorithm_coder_directive_distributed_align(self):
        orc, m = _orc("align")
        await orc.execute("align", [_img()], [], directives=AgentDirectives(algorithm_coder="tmpl"))
        m["algorithm_coder_align"].set_directive.assert_called_with("tmpl")

    @pytest.mark.anyio
    async def test_none_directive_not_distributed(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [], directives=AgentDirectives())
        m["spec_agent"].set_directive.assert_not_called()

    @pytest.mark.anyio
    async def test_no_directives_arg_no_crash(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert result is not None


# ── Goal validation ──────────────────────────────────────────────────────────

class TestGoalValidation:
    @pytest.mark.anyio
    async def test_extreme_accuracy_warns(self):
        orc, m = _orc()
        m["spec_agent"].execute = AsyncMock(return_value=SpecResult(
            mode=InspectionMode.inspection, goal="x",
            success_criteria={"accuracy": 0.999},
        ))
        result = await orc.execute("detect", [_img()], [])
        assert len(result.get("warnings", [])) > 0

    @pytest.mark.anyio
    async def test_extreme_fp_rate_warns(self):
        orc, m = _orc()
        m["spec_agent"].execute = AsyncMock(return_value=SpecResult(
            mode=InspectionMode.inspection, goal="x",
            success_criteria={"fp_rate": 0.0001},
        ))
        result = await orc.execute("detect", [_img()], [])
        assert len(result.get("warnings", [])) > 0

    @pytest.mark.anyio
    async def test_extreme_fn_rate_warns(self):
        orc, m = _orc()
        m["spec_agent"].execute = AsyncMock(return_value=SpecResult(
            mode=InspectionMode.inspection, goal="x",
            success_criteria={"fn_rate": 0.0001},
        ))
        result = await orc.execute("detect", [_img()], [])
        assert len(result.get("warnings", [])) > 0

    @pytest.mark.anyio
    async def test_extreme_coord_error_warns(self):
        orc, m = _orc("align")
        m["spec_agent"].execute = AsyncMock(return_value=SpecResult(
            mode=InspectionMode.align, goal="x",
            success_criteria={"coord_error": 0.1},
        ))
        result = await orc.execute("align", [_img()], [])
        assert len(result.get("warnings", [])) > 0

    @pytest.mark.anyio
    async def test_normal_criteria_no_warnings(self):
        orc, _ = _orc()
        result = await orc.execute("detect", [_img()], [])
        assert len(result.get("warnings", [])) == 0

    def test_validate_goals_handles_none_criteria_values(self):
        orc, _ = _orc()
        spec = SpecResult(
            mode=InspectionMode.inspection,
            goal="test",
            success_criteria={"accuracy": None, "fp_rate": None, "fn_rate": None, "coord_error": None},
        )
        warnings = orc._validate_goals(spec)
        assert isinstance(warnings, list)


# ── Inspection pipeline ──────────────────────────────────────────────────────

class TestInspectionPipeline:
    @pytest.mark.anyio
    async def test_spec_agent_called_with_purpose_text(self):
        orc, m = _orc()
        await orc.execute("detect scratches", [_img()], [])
        m["spec_agent"].execute.assert_called_once_with(user_text="detect scratches")

    @pytest.mark.anyio
    async def test_image_analysis_called_with_first_image(self):
        orc, m = _orc()
        img = _img()
        await orc.execute("detect", [img], [])
        called_img = m["image_analysis_agent"].execute.call_args.args[0]
        assert called_img is img

    @pytest.mark.anyio
    async def test_pipeline_composer_called_with_diagnosis(self):
        orc, m = _orc()
        diag = _diagnosis()
        m["image_analysis_agent"].execute.return_value = diag
        await orc.execute("detect", [_img()], [])
        m["pipeline_composer"].execute.assert_called_once_with(diag)

    @pytest.mark.anyio
    async def test_parameter_searcher_called_per_pipeline(self):
        orc, m = _orc()
        m["pipeline_composer"].execute.return_value = [_pipeline("a"), _pipeline("b"), _pipeline("c")]
        await orc.execute("detect", [_img()], [])
        assert m["parameter_searcher"].execute.call_count == 3

    @pytest.mark.anyio
    async def test_vision_judge_called_per_pipeline(self):
        orc, m = _orc()
        m["pipeline_composer"].execute.return_value = [_pipeline("a"), _pipeline("b")]
        await orc.execute("detect", [_img()], [])
        assert m["vision_judge_agent"].execute.call_count == 2

    @pytest.mark.anyio
    async def test_inspection_plan_agent_called(self):
        orc, m = _orc("inspection")
        await orc.execute("detect", [_img()], [])
        m["inspection_plan_agent"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_algorithm_selector_called(self):
        orc, m = _orc("inspection")
        await orc.execute("detect", [_img()], [])
        m["algorithm_selector"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_coder_inspection_called(self):
        orc, m = _orc("inspection")
        await orc.execute("detect", [_img()], [])
        m["algorithm_coder_inspection"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_code_validator_called(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [])
        m["code_validator"].validate.assert_called_once()

    @pytest.mark.anyio
    async def test_test_agent_inspection_called(self):
        orc, m = _orc("inspection")
        await orc.execute("detect", [_img()], [])
        m["test_agent_inspection"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_evaluation_agent_called(self):
        orc, m = _orc()
        await orc.execute("detect", [_img()], [])
        m["evaluation_agent"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_result_has_all_inspection_keys(self):
        orc, _ = _orc("inspection")
        result = await orc.execute("detect", [_img()], [])
        for key in ["spec_result", "diagnosis", "best_pipeline", "judge_result",
                    "inspection_plan", "algorithm_category", "algorithm_result",
                    "code_validation", "test_results", "evaluation_result", "warnings"]:
            assert key in result, f"missing key: {key}"

    @pytest.mark.anyio
    async def test_align_agents_not_called_in_inspection(self):
        orc, m = _orc("inspection")
        await orc.execute("detect", [_img()], [])
        m["algorithm_coder_align"].execute.assert_not_called()
        m["test_agent_align"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_code_validator_called_with_inspection_mode(self):
        orc, m = _orc("inspection")
        await orc.execute("detect", [_img()], [])
        args = m["code_validator"].validate.call_args
        assert "inspection" in args.args or "inspection" in args.kwargs.values()


# ── Align pipeline ───────────────────────────────────────────────────────────

class TestAlignPipeline:
    @pytest.mark.anyio
    async def test_coder_align_called(self):
        orc, m = _orc("align")
        await orc.execute("align part", [_img()], [])
        m["algorithm_coder_align"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_test_agent_align_called(self):
        orc, m = _orc("align")
        await orc.execute("align part", [_img()], [])
        m["test_agent_align"].execute.assert_called_once()

    @pytest.mark.anyio
    async def test_inspection_plan_not_called_in_align(self):
        orc, m = _orc("align")
        await orc.execute("align part", [_img()], [])
        m["inspection_plan_agent"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_algorithm_selector_not_called_in_align(self):
        orc, m = _orc("align")
        await orc.execute("align part", [_img()], [])
        m["algorithm_selector"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_coder_inspection_not_called_in_align(self):
        orc, m = _orc("align")
        await orc.execute("align part", [_img()], [])
        m["algorithm_coder_inspection"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_test_inspection_not_called_in_align(self):
        orc, m = _orc("align")
        await orc.execute("align part", [_img()], [])
        m["test_agent_inspection"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_align_result_inspection_plan_is_none(self):
        orc, _ = _orc("align")
        result = await orc.execute("align", [_img()], [])
        assert result.get("inspection_plan") is None

    @pytest.mark.anyio
    async def test_align_result_algorithm_category_is_none(self):
        orc, _ = _orc("align")
        result = await orc.execute("align", [_img()], [])
        assert result.get("algorithm_category") is None

    @pytest.mark.anyio
    async def test_code_validator_called_with_align_mode(self):
        orc, m = _orc("align")
        await orc.execute("align", [_img()], [])
        args = m["code_validator"].validate.call_args
        assert "align" in args.args or "align" in args.kwargs.values()


# ── Pipeline selection ───────────────────────────────────────────────────────

class TestPipelineSelection:
    @pytest.mark.anyio
    async def test_highest_judge_avg_wins(self):
        orc, m = _orc()
        m["pipeline_composer"].execute.return_value = [_pipeline("low"), _pipeline("high")]
        m["vision_judge_agent"].execute = AsyncMock(
            side_effect=[_judge(0.3, 0.3, 0.3), _judge(0.9, 0.9, 0.9)]
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["best_pipeline"].name == "high"

    @pytest.mark.anyio
    async def test_first_pipeline_wins_when_tied(self):
        orc, m = _orc()
        m["pipeline_composer"].execute.return_value = [_pipeline("first"), _pipeline("second")]
        m["vision_judge_agent"].execute = AsyncMock(return_value=_judge(0.5, 0.5, 0.5))
        result = await orc.execute("detect", [_img()], [])
        assert result["best_pipeline"].name == "first"

    @pytest.mark.anyio
    async def test_judge_result_in_output_matches_best_pipeline(self):
        orc, m = _orc()
        m["pipeline_composer"].execute.return_value = [_pipeline("low"), _pipeline("high")]
        judge_low = _judge(0.2, 0.2, 0.2)
        judge_high = _judge(0.9, 0.9, 0.9)
        m["vision_judge_agent"].execute = AsyncMock(side_effect=[judge_low, judge_high])
        result = await orc.execute("detect", [_img()], [])
        assert result["judge_result"].visibility_score == 0.9


# ── Code validation failure ──────────────────────────────────────────────────

class TestCodeValidationFailure:
    @pytest.mark.anyio
    async def test_invalid_code_skips_test_inspection(self):
        orc, m = _orc("inspection")
        m["code_validator"].validate.return_value = ValidationResult(
            is_valid=False, errors=["syntax error"]
        )
        await orc.execute("detect", [_img()], [])
        m["test_agent_inspection"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_invalid_code_skips_test_align(self):
        orc, m = _orc("align")
        m["code_validator"].validate.return_value = ValidationResult(
            is_valid=False, errors=["no valid align(image) function"]
        )
        await orc.execute("align", [_img()], [])
        m["test_agent_align"].execute.assert_not_called()

    @pytest.mark.anyio
    async def test_invalid_code_evaluation_overall_failed(self):
        orc, m = _orc()
        m["code_validator"].validate.return_value = ValidationResult(
            is_valid=False, errors=["error"]
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].overall_passed is False

    @pytest.mark.anyio
    async def test_invalid_code_sets_algorithm_runtime_error_reason(self):
        orc, m = _orc()
        m["code_validator"].validate.return_value = ValidationResult(
            is_valid=False, errors=["error"]
        )
        result = await orc.execute("detect", [_img()], [])
        assert result["evaluation_result"].failure_reason == FailureReason.algorithm_runtime_error

    @pytest.mark.anyio
    async def test_invalid_code_skips_evaluation_agent(self):
        orc, m = _orc()
        m["code_validator"].validate.return_value = ValidationResult(
            is_valid=False, errors=["error"]
        )
        await orc.execute("detect", [_img()], [])
        m["evaluation_agent"].execute.assert_not_called()


# ── Progress tracking ────────────────────────────────────────────────────────

class TestProgressTracking:
    def test_initial_status_idle(self):
        orc, _ = _orc()
        assert orc.get_progress().status == "idle"

    def test_initial_current_agent_empty(self):
        orc, _ = _orc()
        assert orc.get_progress().current_agent == ""

    @pytest.mark.anyio
    async def test_status_success_after_passed_evaluation(self):
        orc, m = _orc()
        m["evaluation_agent"].execute.return_value = _eval_result(True)
        await orc.execute("detect", [_img()], [])
        assert orc.get_progress().status == "success"

    @pytest.mark.anyio
    async def test_status_failed_after_failed_evaluation(self):
        orc, m = _orc()
        m["evaluation_agent"].execute.return_value = _eval_result(False)
        await orc.execute("detect", [_img()], [])
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_status_failed_when_validation_fails(self):
        orc, m = _orc()
        m["code_validator"].validate.return_value = ValidationResult(
            is_valid=False, errors=["error"]
        )
        await orc.execute("detect", [_img()], [])
        assert orc.get_progress().status == "failed"

    @pytest.mark.anyio
    async def test_status_transitions_through_running(self):
        statuses: list[str] = []
        orc, m = _orc()
        original = m["evaluation_agent"].execute

        def capture(*args, **kwargs):
            statuses.append(orc.get_progress().status)
            return original(*args, **kwargs)

        m["evaluation_agent"].execute = capture
        await orc.execute("detect", [_img()], [])
        assert "running" in statuses


# ── Error handling ───────────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.mark.anyio
    async def test_spec_agent_exception_propagates(self):
        orc, m = _orc()
        m["spec_agent"].execute = AsyncMock(side_effect=RuntimeError("spec failed"))
        with pytest.raises(RuntimeError, match="spec failed"):
            await orc.execute("detect", [_img()], [])

    @pytest.mark.anyio
    async def test_image_analysis_exception_propagates(self):
        orc, m = _orc()
        m["image_analysis_agent"].execute = Mock(side_effect=ValueError("analysis failed"))
        with pytest.raises(ValueError, match="analysis failed"):
            await orc.execute("detect", [_img()], [])

    @pytest.mark.anyio
    async def test_vision_judge_exception_propagates(self):
        orc, m = _orc()
        m["vision_judge_agent"].execute = AsyncMock(side_effect=RuntimeError("judge failed"))
        with pytest.raises(RuntimeError, match="judge failed"):
            await orc.execute("detect", [_img()], [])

    @pytest.mark.anyio
    async def test_progress_failed_on_exception(self):
        orc, m = _orc()
        m["spec_agent"].execute = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            await orc.execute("detect", [_img()], [])
        assert orc.get_progress().status == "failed"


# ── Logging ──────────────────────────────────────────────────────────────────

class TestLogging:
    @pytest.mark.anyio
    async def test_orchestrator_writes_logs(self):
        from backend.services.logger import via_logger
        via_logger.clear()
        orc, _ = _orc()
        await orc.execute("detect", [_img()], [])
        logs = via_logger.get_logs(agent="orchestrator")
        assert len(logs) > 0

    @pytest.mark.anyio
    async def test_orchestrator_logs_on_failure(self):
        from backend.services.logger import via_logger
        via_logger.clear()
        orc, m = _orc()
        m["spec_agent"].execute = AsyncMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            await orc.execute("detect", [_img()], [])
        logs = via_logger.get_logs(agent="orchestrator")
        assert any(l["level"] == "ERROR" for l in logs)
