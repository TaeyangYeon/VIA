"""Tests for agents/models.py and agents/base_agent.py — Step 11."""
import dataclasses
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Enums ────────────────────────────────────────────────────────────────────

class TestInspectionMode:
    def test_members(self):
        from agents.models import InspectionMode
        assert set(m.value for m in InspectionMode) == {"inspection", "align"}

    def test_str_compatible(self):
        from agents.models import InspectionMode
        assert InspectionMode.inspection == "inspection"
        assert InspectionMode.align == "align"

    def test_is_str_enum(self):
        from agents.models import InspectionMode
        assert isinstance(InspectionMode.inspection, str)


class TestAlgorithmCategory:
    def test_members(self):
        from agents.models import AlgorithmCategory
        values = {m.value for m in AlgorithmCategory}
        assert "BLOB" in values
        assert "COLOR_FILTER" in values
        assert "EDGE_DETECTION" in values
        assert "TEMPLATE_MATCHING" in values
        assert len(values) == 4

    def test_str_compatible(self):
        from agents.models import AlgorithmCategory
        assert AlgorithmCategory.BLOB == "BLOB"
        assert AlgorithmCategory.COLOR_FILTER == "COLOR_FILTER"
        assert AlgorithmCategory.EDGE_DETECTION == "EDGE_DETECTION"
        assert AlgorithmCategory.TEMPLATE_MATCHING == "TEMPLATE_MATCHING"

    def test_is_str_enum(self):
        from agents.models import AlgorithmCategory
        assert isinstance(AlgorithmCategory.BLOB, str)


class TestFailureReason:
    def test_members(self):
        from agents.models import FailureReason
        values = {m.value for m in FailureReason}
        expected = {
            "pipeline_bad_fit",
            "pipeline_bad_params",
            "algorithm_wrong_category",
            "algorithm_runtime_error",
            "inspection_plan_issue",
            "spec_issue",
        }
        assert values == expected

    def test_str_compatible(self):
        from agents.models import FailureReason
        assert FailureReason.pipeline_bad_fit == "pipeline_bad_fit"
        assert FailureReason.spec_issue == "spec_issue"


class TestDecisionType:
    def test_members(self):
        from agents.models import DecisionType
        values = {m.value for m in DecisionType}
        assert values == {"rule_based", "edge_learning", "deep_learning", "hw_improvement"}

    def test_str_compatible(self):
        from agents.models import DecisionType
        assert DecisionType.rule_based == "rule_based"
        assert DecisionType.deep_learning == "deep_learning"


class TestDefectScale:
    def test_members(self):
        from agents.models import DefectScale
        values = {m.value for m in DefectScale}
        assert values == {"macro", "micro", "texture"}

    def test_str_compatible(self):
        from agents.models import DefectScale
        assert DefectScale.macro == "macro"
        assert DefectScale.texture == "texture"


class TestIlluminationType:
    def test_members(self):
        from agents.models import IlluminationType
        values = {m.value for m in IlluminationType}
        assert values == {"uniform", "gradient", "spot", "uneven"}

    def test_str_compatible(self):
        from agents.models import IlluminationType
        assert IlluminationType.uniform == "uniform"
        assert IlluminationType.spot == "spot"


class TestNoiseFrequency:
    def test_members(self):
        from agents.models import NoiseFrequency
        values = {m.value for m in NoiseFrequency}
        assert values == {"high_freq", "low_freq"}

    def test_str_compatible(self):
        from agents.models import NoiseFrequency
        assert NoiseFrequency.high_freq == "high_freq"
        assert NoiseFrequency.low_freq == "low_freq"


# ── Dataclasses ───────────────────────────────────────────────────────────────

class TestImageDiagnosis:
    def _make(self):
        from agents.models import ImageDiagnosis, IlluminationType, NoiseFrequency, DefectScale
        return ImageDiagnosis(
            contrast=0.5,
            noise_level=0.1,
            edge_density=0.3,
            lighting_uniformity=0.8,
            illumination_type=IlluminationType.uniform,
            noise_frequency=NoiseFrequency.high_freq,
            reflection_level=0.2,
            texture_complexity=0.4,
            surface_type="metal",
            defect_scale=DefectScale.macro,
            blob_feasibility=0.7,
            blob_count_estimate=5,
            blob_size_variance=0.15,
            color_discriminability=0.6,
            dominant_channel_ratio=0.55,
            structural_regularity=0.9,
            pattern_repetition=0.1,
            background_uniformity=0.85,
            optimal_color_space="HSV",
            threshold_candidate=128.0,
            edge_sharpness=0.75,
        )

    def test_instantiation(self):
        obj = self._make()
        assert obj is not None

    def test_exactly_21_fields(self):
        from agents.models import ImageDiagnosis
        fields = dataclasses.fields(ImageDiagnosis)
        assert len(fields) == 21

    def test_field_names(self):
        from agents.models import ImageDiagnosis
        names = {f.name for f in dataclasses.fields(ImageDiagnosis)}
        expected = {
            "contrast", "noise_level", "edge_density", "lighting_uniformity",
            "illumination_type", "noise_frequency", "reflection_level",
            "texture_complexity", "surface_type", "defect_scale",
            "blob_feasibility", "blob_count_estimate", "blob_size_variance",
            "color_discriminability", "dominant_channel_ratio",
            "structural_regularity", "pattern_repetition",
            "background_uniformity", "optimal_color_space",
            "threshold_candidate", "edge_sharpness",
        }
        assert names == expected

    def test_field_values(self):
        from agents.models import IlluminationType, NoiseFrequency, DefectScale
        obj = self._make()
        assert obj.contrast == 0.5
        assert obj.blob_count_estimate == 5
        assert obj.illumination_type == IlluminationType.uniform
        assert obj.noise_frequency == NoiseFrequency.high_freq
        assert obj.defect_scale == DefectScale.macro
        assert obj.surface_type == "metal"
        assert obj.optimal_color_space == "HSV"

    def test_is_dataclass(self):
        from agents.models import ImageDiagnosis
        assert dataclasses.is_dataclass(ImageDiagnosis)


class TestPipelineBlock:
    def test_instantiation_all_fields(self):
        from agents.models import PipelineBlock
        b = PipelineBlock(name="blur", params={"ksize": 3}, when_condition="always")
        assert b.name == "blur"
        assert b.params == {"ksize": 3}
        assert b.when_condition == "always"

    def test_params_optional_defaults_none(self):
        from agents.models import PipelineBlock
        b = PipelineBlock(name="edge", when_condition="if_noisy")
        assert b.params is None

    def test_is_dataclass(self):
        from agents.models import PipelineBlock
        assert dataclasses.is_dataclass(PipelineBlock)


class TestProcessingPipeline:
    def test_instantiation(self):
        from agents.models import ProcessingPipeline, PipelineBlock
        b = PipelineBlock(name="blur", when_condition="always")
        p = ProcessingPipeline(blocks=[b], name="test_pipe", score=0.8)
        assert p.name == "test_pipe"
        assert p.score == 0.8
        assert len(p.blocks) == 1

    def test_score_defaults_zero(self):
        from agents.models import ProcessingPipeline
        p = ProcessingPipeline(blocks=[], name="pipe")
        assert p.score == 0.0

    def test_blocks_field(self):
        from agents.models import ProcessingPipeline
        p1 = ProcessingPipeline(blocks=[], name="a")
        p2 = ProcessingPipeline(blocks=[], name="b")
        p1.blocks.append("x")
        assert p2.blocks == [], "mutable default must be field(default_factory=list)"

    def test_is_dataclass(self):
        from agents.models import ProcessingPipeline
        assert dataclasses.is_dataclass(ProcessingPipeline)


class TestJudgementResult:
    def test_instantiation(self):
        from agents.models import JudgementResult
        j = JudgementResult(
            visibility_score=0.9,
            separability_score=0.8,
            measurability_score=0.7,
            problems=["blur"],
            next_suggestion="increase contrast",
        )
        assert j.visibility_score == 0.9
        assert j.problems == ["blur"]

    def test_problems_list_independent(self):
        from agents.models import JudgementResult
        j1 = JudgementResult(0.9, 0.8, 0.7, [], "ok")
        j2 = JudgementResult(0.9, 0.8, 0.7, [], "ok")
        j1.problems.append("x")
        assert j2.problems == []

    def test_is_dataclass(self):
        from agents.models import JudgementResult
        assert dataclasses.is_dataclass(JudgementResult)


class TestInspectionItem:
    def test_instantiation(self):
        from agents.models import InspectionItem, AlgorithmCategory
        item = InspectionItem(
            id=1,
            name="scratch_detect",
            purpose="find scratches",
            method=AlgorithmCategory.EDGE_DETECTION,
            depends_on=[],
            safety_role="primary",
            success_criteria="FP<0.01",
        )
        assert item.id == 1
        assert item.method == AlgorithmCategory.EDGE_DETECTION

    def test_depends_on_list_independent(self):
        from agents.models import InspectionItem, AlgorithmCategory
        i1 = InspectionItem(1, "a", "p", AlgorithmCategory.BLOB, [], "r", "c")
        i2 = InspectionItem(2, "b", "p", AlgorithmCategory.BLOB, [], "r", "c")
        i1.depends_on.append(99)
        assert i2.depends_on == []

    def test_is_dataclass(self):
        from agents.models import InspectionItem
        assert dataclasses.is_dataclass(InspectionItem)


class TestInspectionPlan:
    def test_instantiation(self):
        from agents.models import InspectionPlan, InspectionMode
        plan = InspectionPlan(items=[], mode=InspectionMode.inspection)
        assert plan.mode == InspectionMode.inspection

    def test_is_dataclass(self):
        from agents.models import InspectionPlan
        assert dataclasses.is_dataclass(InspectionPlan)


class TestSpecResult:
    def test_instantiation(self):
        from agents.models import SpecResult, InspectionMode
        s = SpecResult(
            mode=InspectionMode.align,
            goal="align part",
            success_criteria={"x_error": "<0.5mm"},
        )
        assert s.mode == InspectionMode.align
        assert s.goal == "align part"

    def test_is_dataclass(self):
        from agents.models import SpecResult
        assert dataclasses.is_dataclass(SpecResult)


class TestTestMetrics:
    def test_all_none_by_default(self):
        from agents.models import TestMetrics
        m = TestMetrics()
        assert m.accuracy is None
        assert m.fp_rate is None
        assert m.fn_rate is None
        assert m.coord_error is None
        assert m.success_rate is None

    def test_instantiation_with_values(self):
        from agents.models import TestMetrics
        m = TestMetrics(accuracy=0.99, fp_rate=0.01, fn_rate=0.02)
        assert m.accuracy == 0.99
        assert m.coord_error is None

    def test_is_dataclass(self):
        from agents.models import TestMetrics
        assert dataclasses.is_dataclass(TestMetrics)


class TestItemTestResult:
    def test_instantiation(self):
        from agents.models import ItemTestResult, TestMetrics
        r = ItemTestResult(
            item_id=1,
            item_name="scratch",
            passed=True,
            metrics=TestMetrics(accuracy=0.99),
        )
        assert r.item_id == 1
        assert r.passed is True
        assert r.details == ""

    def test_details_defaults_empty_string(self):
        from agents.models import ItemTestResult, TestMetrics
        r = ItemTestResult(1, "a", False, TestMetrics())
        assert r.details == ""

    def test_is_dataclass(self):
        from agents.models import ItemTestResult
        assert dataclasses.is_dataclass(ItemTestResult)


class TestEvaluationResult:
    def test_instantiation(self):
        from agents.models import EvaluationResult, FailureReason
        e = EvaluationResult(
            overall_passed=False,
            failure_reason=FailureReason.pipeline_bad_fit,
            failed_items=[1, 2],
            analysis="pipeline not fitting",
        )
        assert e.overall_passed is False
        assert e.failure_reason == FailureReason.pipeline_bad_fit

    def test_failure_reason_optional(self):
        from agents.models import EvaluationResult
        e = EvaluationResult(overall_passed=True, failure_reason=None, failed_items=[], analysis="ok")
        assert e.failure_reason is None

    def test_failed_items_list_independent(self):
        from agents.models import EvaluationResult
        e1 = EvaluationResult(True, None, [], "ok")
        e2 = EvaluationResult(True, None, [], "ok")
        e1.failed_items.append(1)
        assert e2.failed_items == []

    def test_is_dataclass(self):
        from agents.models import EvaluationResult
        assert dataclasses.is_dataclass(EvaluationResult)


class TestFeedbackAction:
    def test_instantiation(self):
        from agents.models import FeedbackAction, FailureReason
        fa = FeedbackAction(
            target_agent="pipeline_composer",
            reason=FailureReason.pipeline_bad_params,
            context={"iteration": 2},
        )
        assert fa.target_agent == "pipeline_composer"
        assert fa.retry_count == 0

    def test_retry_count_defaults_zero(self):
        from agents.models import FeedbackAction, FailureReason
        fa = FeedbackAction("agent", FailureReason.spec_issue, {})
        assert fa.retry_count == 0

    def test_is_dataclass(self):
        from agents.models import FeedbackAction
        assert dataclasses.is_dataclass(FeedbackAction)


class TestDecisionResult:
    def test_instantiation(self):
        from agents.models import DecisionResult, DecisionType
        d = DecisionResult(
            decision=DecisionType.edge_learning,
            reason="accuracy insufficient",
            confidence=0.85,
            details={"metric": 0.72},
        )
        assert d.decision == DecisionType.edge_learning
        assert d.confidence == 0.85

    def test_is_dataclass(self):
        from agents.models import DecisionResult
        assert dataclasses.is_dataclass(DecisionResult)


class TestAgentDirectives:
    def test_all_none_by_default(self):
        from agents.models import AgentDirectives
        d = AgentDirectives()
        for field in dataclasses.fields(d):
            assert getattr(d, field.name) is None, f"{field.name} should default to None"

    def test_has_eight_fields(self):
        from agents.models import AgentDirectives
        assert len(dataclasses.fields(AgentDirectives)) == 8

    def test_field_names(self):
        from agents.models import AgentDirectives
        names = {f.name for f in dataclasses.fields(AgentDirectives)}
        expected = {
            "orchestrator", "spec", "image_analysis", "pipeline_composer",
            "vision_judge", "inspection_plan", "algorithm_coder", "test",
        }
        assert names == expected

    def test_set_fields(self):
        from agents.models import AgentDirectives
        d = AgentDirectives(orchestrator="be thorough", spec="identify defect type")
        assert d.orchestrator == "be thorough"
        assert d.spec == "identify defect type"
        assert d.test is None

    def test_is_dataclass(self):
        from agents.models import AgentDirectives
        assert dataclasses.is_dataclass(AgentDirectives)


class TestExecutionProgress:
    def test_instantiation(self):
        from agents.models import ExecutionProgress
        p = ExecutionProgress(
            current_agent="spec",
            current_iteration=1,
            status="running",
            message="processing",
        )
        assert p.current_agent == "spec"
        assert p.current_iteration == 1

    def test_is_dataclass(self):
        from agents.models import ExecutionProgress
        assert dataclasses.is_dataclass(ExecutionProgress)


class TestAlgorithmResult:
    def test_instantiation(self):
        from agents.models import AlgorithmResult, AlgorithmCategory, ProcessingPipeline
        r = AlgorithmResult(
            code="def detect(): pass",
            explanation="detects blobs",
            category=AlgorithmCategory.BLOB,
            pipeline=ProcessingPipeline(blocks=[], name="pipe"),
        )
        assert r.code == "def detect(): pass"
        assert r.category == AlgorithmCategory.BLOB

    def test_is_dataclass(self):
        from agents.models import AlgorithmResult
        assert dataclasses.is_dataclass(AlgorithmResult)


# ── BaseAgent ─────────────────────────────────────────────────────────────────

class TestBaseAgentAbstract:
    def test_cannot_instantiate_directly(self):
        from agents.base_agent import BaseAgent
        with pytest.raises(TypeError):
            BaseAgent(name="test")  # type: ignore[abstract]

    def test_subclass_without_execute_raises(self):
        from agents.base_agent import BaseAgent

        class Incomplete(BaseAgent):
            pass

        with pytest.raises(TypeError):
            Incomplete(name="incomplete")

    def test_concrete_subclass_can_instantiate(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            async def execute(self, **kwargs) -> dict:
                return {}

        agent = ConcreteAgent(name="concrete")
        assert agent is not None


class TestBaseAgentProperties:
    def _make_agent(self, name="test_agent", directive=None):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            async def execute(self, **kwargs) -> dict:
                return {}

        return ConcreteAgent(name=name, directive=directive)

    def test_agent_name_property(self):
        agent = self._make_agent(name="spec_agent")
        assert agent.agent_name == "spec_agent"

    def test_get_directive_none_by_default(self):
        agent = self._make_agent()
        assert agent.get_directive() is None

    def test_get_directive_with_value(self):
        agent = self._make_agent(directive="focus on edges")
        assert agent.get_directive() == "focus on edges"

    def test_set_directive(self):
        agent = self._make_agent()
        agent.set_directive("new directive")
        assert agent.get_directive() == "new directive"

    def test_set_directive_overwrites(self):
        agent = self._make_agent(directive="old")
        agent.set_directive("new")
        assert agent.get_directive() == "new"


class TestBaseAgentLog:
    def _make_agent(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            async def execute(self, **kwargs) -> dict:
                return {}

        return ConcreteAgent(name="logger_agent")

    def test_log_calls_via_logger(self):
        agent = self._make_agent()
        with patch("agents.base_agent.via_logger") as mock_logger:
            agent._log("INFO", "test message")
            mock_logger.log.assert_called_once_with(
                "logger_agent", "INFO", "test message", None
            )

    def test_log_with_details(self):
        agent = self._make_agent()
        with patch("agents.base_agent.via_logger") as mock_logger:
            details = {"key": "value"}
            agent._log("ERROR", "something failed", details)
            mock_logger.log.assert_called_once_with(
                "logger_agent", "ERROR", "something failed", details
            )

    def test_log_uses_agent_name(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            async def execute(self, **kwargs) -> dict:
                return {}

        agent = ConcreteAgent(name="my_custom_agent")
        with patch("agents.base_agent.via_logger") as mock_logger:
            agent._log("DEBUG", "debug info")
            call_args = mock_logger.log.call_args[0]
            assert call_args[0] == "my_custom_agent"
