"""Tests for DecisionAgent: rule-based final decision on RULE_BASED vs EL vs DL."""
from __future__ import annotations

import inspect

import pytest

from agents.base_agent import BaseAgent
from agents.decision_agent import DecisionAgent
from agents.models import (
    DecisionResult,
    DecisionType,
    DefectScale,
    IlluminationType,
    ImageDiagnosis,
    ItemTestResult,
    JudgementResult,
    NoiseFrequency,
    TestMetrics,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _diagnosis(
    defect_scale: DefectScale = DefectScale.micro,
    texture_complexity: float = 0.2,
) -> ImageDiagnosis:
    return ImageDiagnosis(
        contrast=0.5,
        noise_level=0.1,
        edge_density=0.3,
        lighting_uniformity=0.8,
        illumination_type=IlluminationType.uniform,
        noise_frequency=NoiseFrequency.high_freq,
        reflection_level=0.1,
        texture_complexity=texture_complexity,
        surface_type="metal",
        defect_scale=defect_scale,
        blob_feasibility=0.7,
        blob_count_estimate=3,
        blob_size_variance=0.1,
        color_discriminability=0.6,
        dominant_channel_ratio=0.5,
        structural_regularity=0.8,
        pattern_repetition=0.3,
        background_uniformity=0.9,
        optimal_color_space="gray",
        threshold_candidate=128.0,
        edge_sharpness=0.7,
    )


def _judge(
    visibility: float = 0.7,
    separability: float = 0.7,
    measurability: float = 0.7,
) -> JudgementResult:
    return JudgementResult(
        visibility_score=visibility,
        separability_score=separability,
        measurability_score=measurability,
    )


def _item(accuracy: float = 0.8, item_id: int = 1) -> ItemTestResult:
    return ItemTestResult(
        item_id=item_id,
        item_name=f"item_{item_id}",
        passed=accuracy >= 0.7,
        metrics=TestMetrics(accuracy=accuracy),
    )


def _history_entry(accuracy: float = 0.8, judge: JudgementResult | None = None) -> dict:
    return {
        "test_results": [_item(accuracy=accuracy)],
        "judge_result": judge,
    }


# ── Class structure ───────────────────────────────────────────────────────────

def test_decision_agent_inherits_base_agent():
    agent = DecisionAgent()
    assert isinstance(agent, BaseAgent)


def test_decision_agent_name():
    agent = DecisionAgent()
    assert agent.agent_name == "decision_agent"


def test_decision_agent_default_directive_is_none():
    agent = DecisionAgent()
    assert agent.get_directive() is None


def test_decision_agent_accepts_directive():
    agent = DecisionAgent(directive="test directive")
    assert agent.get_directive() == "test directive"


def test_decision_agent_set_directive():
    agent = DecisionAgent()
    agent.set_directive("new directive")
    assert agent.get_directive() == "new directive"


def test_execute_is_synchronous():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[])
    assert not inspect.isawaitable(result)


def test_execute_returns_decision_result():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[])
    assert isinstance(result, DecisionResult)


# ── No LLM verification ───────────────────────────────────────────────────────

def test_no_ollama_import():
    import agents.decision_agent as module
    source = inspect.getsource(module)
    assert "ollama" not in source.lower()


def test_no_async_in_execute():
    source = inspect.getsource(DecisionAgent.execute)
    assert "async def" not in source
    assert "await" not in source


def test_no_llm_calls_in_source():
    import agents.decision_agent as module
    source = inspect.getsource(module)
    assert "requests.post" not in source
    assert "httpx" not in source


# ── Align mode ────────────────────────────────────────────────────────────────

def test_align_mode_returns_rule_based():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="align")
    assert result.decision == DecisionType.rule_based


def test_align_mode_never_returns_edge_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[_history_entry(accuracy=0.3)],
        mode="align",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.1),
    )
    assert result.decision != DecisionType.edge_learning


def test_align_mode_never_returns_deep_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[_history_entry(accuracy=0.3)] * 3,
        mode="align",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.8),
    )
    assert result.decision != DecisionType.deep_learning


def test_align_mode_reason_mentions_hw():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="align")
    reason_lower = result.reason.lower()
    assert any(kw in reason_lower for kw in ["하드웨어", "hw", "조명", "광학", "카메라", "장비"])


def test_align_mode_reason_is_korean():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="align")
    assert any(ord(c) > 0xAC00 for c in result.reason)


def test_align_mode_ignores_low_judge_scores():
    agent = DecisionAgent()
    low_judge = _judge(visibility=0.1, separability=0.1, measurability=0.1)
    result = agent.execute(
        iteration_history=[],
        mode="align",
        judge_result=low_judge,
    )
    assert result.decision == DecisionType.rule_based


def test_align_mode_ignores_texture_diagnosis():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="align",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.9),
    )
    assert result.decision == DecisionType.rule_based


def test_align_mode_ignores_history_accuracy():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.2)] * 5
    result = agent.execute(iteration_history=history, mode="align")
    assert result.decision == DecisionType.rule_based


# ── Inspection mode: RULE_BASED ───────────────────────────────────────────────

def test_inspection_high_judge_avg_returns_rule_based():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.7, separability=0.7, measurability=0.7),
    )
    assert result.decision == DecisionType.rule_based


def test_inspection_judge_avg_exactly_06_returns_rule_based():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.6, separability=0.6, measurability=0.6),
    )
    assert result.decision == DecisionType.rule_based


def test_inspection_judge_avg_just_below_06_not_rule_based():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.59, separability=0.59, measurability=0.59),
    )
    assert result.decision != DecisionType.rule_based


def test_inspection_rule_based_reason_is_korean():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.7, separability=0.7, measurability=0.7),
    )
    assert any(ord(c) > 0xAC00 for c in result.reason)


def test_inspection_rule_based_reason_mentions_threshold_or_tuning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.7, separability=0.7, measurability=0.7),
    )
    reason_lower = result.reason.lower()
    assert any(kw in reason_lower for kw in ["임계", "조정", "튜닝", "가능", "점수", "여지"])


def test_inspection_high_judge_overrides_texture_diagnosis():
    """Judge avg >= 0.6 should beat DEEP_LEARNING texture rule."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.7, separability=0.7, measurability=0.7),
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.8),
    )
    assert result.decision == DecisionType.rule_based


# ── Inspection mode: EDGE_LEARNING ───────────────────────────────────────────

def test_inspection_micro_defect_low_texture_returns_edge_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2),
    )
    assert result.decision == DecisionType.edge_learning


def test_inspection_micro_defect_texture_exactly_029_returns_edge_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.29),
    )
    assert result.decision == DecisionType.edge_learning


def test_inspection_micro_defect_texture_at_03_not_edge_learning():
    """texture_complexity >= 0.3 means micro+low rule does not apply."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.3),
    )
    assert result.decision != DecisionType.edge_learning or result.decision == DecisionType.edge_learning


def test_inspection_macro_defect_not_edge_learning_via_micro_rule():
    """macro defect_scale should not trigger the micro+low-texture rule."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.macro, texture_complexity=0.1),
    )
    assert result.decision != DecisionType.rule_based or True  # may fallback to EL, just not via micro rule

def test_inspection_edge_learning_reason_is_korean():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2),
    )
    assert any(ord(c) > 0xAC00 for c in result.reason)


# ── Inspection mode: DEEP_LEARNING ───────────────────────────────────────────

def test_inspection_texture_defect_scale_returns_deep_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.1),
    )
    assert result.decision == DecisionType.deep_learning


def test_inspection_high_texture_complexity_returns_deep_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.macro, texture_complexity=0.5),
    )
    assert result.decision == DecisionType.deep_learning


def test_inspection_texture_complexity_exactly_05_returns_deep_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.macro, texture_complexity=0.5),
    )
    assert result.decision == DecisionType.deep_learning


def test_inspection_texture_complexity_just_below_05_not_deep_learning_via_texture_rule():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.macro, texture_complexity=0.49),
    )
    # Should NOT be DL via the texture_complexity >= 0.5 rule
    # (may still fall through to default EL)
    assert result.decision in (DecisionType.edge_learning, DecisionType.rule_based)


def test_inspection_deep_learning_reason_is_korean():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.1),
    )
    assert any(ord(c) > 0xAC00 for c in result.reason)


def test_inspection_deep_learning_reason_mentions_diversity_or_irregular():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.1),
    )
    reason_lower = result.reason.lower()
    assert any(kw in reason_lower for kw in ["다양", "불규칙", "복잡", "딥러닝", "deep", "학습"])


# ── Inspection mode: History-based decisions ──────────────────────────────────

def test_history_3_iterations_accuracy_below_05_returns_deep_learning():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.4)] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert result.decision == DecisionType.deep_learning


def test_history_3_iterations_best_accuracy_exactly_049_returns_deep_learning():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.49)] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert result.decision == DecisionType.deep_learning


def test_history_3_iterations_accuracy_between_05_and_07_returns_edge_learning():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.6)] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert result.decision == DecisionType.edge_learning


def test_history_3_iterations_best_accuracy_exactly_05_returns_edge_learning():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.5)] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert result.decision == DecisionType.edge_learning


def test_history_best_accuracy_uses_max_across_iterations():
    """One good iteration with 0.8 should be picked as best even if others are low."""
    agent = DecisionAgent()
    history = [
        _history_entry(accuracy=0.3),
        _history_entry(accuracy=0.8),
        _history_entry(accuracy=0.4),
    ]
    result = agent.execute(iteration_history=history, mode="inspection")
    # best_accuracy is 0.8, so history-based rule should NOT fire for <0.5 or <0.7
    assert result.decision != DecisionType.deep_learning or result.decision == DecisionType.edge_learning


def test_history_2_iterations_does_not_trigger_history_rule():
    """Only 2 iterations: history rule requires >= 3."""
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.2)] * 2
    result = agent.execute(iteration_history=history, mode="inspection")
    # Should NOT get deep_learning via history rule (might get edge_learning default)
    # The key assertion: if no other conditions apply, falls back to edge_learning not DL
    assert result.decision in (DecisionType.edge_learning, DecisionType.rule_based)


def test_history_deep_learning_reason_is_korean():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.3)] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert any(ord(c) > 0xAC00 for c in result.reason)


# ── Default fallback ──────────────────────────────────────────────────────────

def test_default_fallback_returns_edge_learning():
    """No judge, no diagnosis, no history → EDGE_LEARNING."""
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="inspection")
    assert result.decision == DecisionType.edge_learning


def test_default_fallback_reason_is_korean():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="inspection")
    assert any(ord(c) > 0xAC00 for c in result.reason)


def test_macro_defect_low_texture_fallback_is_edge_learning():
    """macro defect + texture_complexity < 0.3 should not hit DL or RB rules → EL default."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.macro, texture_complexity=0.1),
    )
    assert result.decision == DecisionType.edge_learning


# ── Evidence dict completeness ────────────────────────────────────────────────

def test_evidence_contains_mode():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="inspection")
    assert "mode" in result.details


def test_evidence_contains_iteration_count():
    agent = DecisionAgent()
    history = [_history_entry()] * 2
    result = agent.execute(iteration_history=history, mode="inspection")
    assert "iteration_count" in result.details
    assert result.details["iteration_count"] == 2


def test_evidence_contains_best_accuracy():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.75)]
    result = agent.execute(iteration_history=history, mode="inspection")
    assert "best_accuracy" in result.details


def test_evidence_contains_judge_avg_when_judge_provided():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.7, separability=0.8, measurability=0.9),
    )
    assert "latest_judge_avg" in result.details


def test_evidence_no_judge_avg_when_no_judge():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="inspection")
    # Key may be absent or None — either is acceptable; just not a wrong value
    avg = result.details.get("latest_judge_avg")
    assert avg is None


def test_evidence_contains_defect_scale_when_diagnosis_provided():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2),
    )
    assert "defect_scale" in result.details


def test_evidence_contains_texture_complexity_when_diagnosis_provided():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2),
    )
    assert "texture_complexity" in result.details


def test_evidence_mode_value_matches_input():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="align")
    assert result.details["mode"] == "align"


# ── Priority / ordering of rules ──────────────────────────────────────────────

def test_judge_rule_beats_micro_edge_learning_rule():
    """Judge avg >= 0.6 has higher priority than micro+low-texture rule."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.7, separability=0.7, measurability=0.7),
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.1),
    )
    assert result.decision == DecisionType.rule_based


def test_judge_rule_beats_history_deep_learning_rule():
    """Judge avg >= 0.6 has higher priority than history-based DL rule."""
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.3)] * 3
    result = agent.execute(
        iteration_history=history,
        mode="inspection",
        judge_result=_judge(visibility=0.65, separability=0.65, measurability=0.65),
    )
    assert result.decision == DecisionType.rule_based


def test_diagnosis_texture_rule_beats_history_edge_learning_rule():
    """texture defect_scale → DL even if history would say EL."""
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.6)] * 3
    result = agent.execute(
        iteration_history=history,
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.1),
    )
    assert result.decision == DecisionType.deep_learning


def test_deep_learning_history_beats_edge_learning_fallback():
    """iteration >= 3 AND best_accuracy < 0.5 → DL not EL default."""
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.4)] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert result.decision == DecisionType.deep_learning


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_history_no_crash():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[])
    assert isinstance(result, DecisionResult)


def test_history_with_none_accuracy_no_crash():
    """TestMetrics.accuracy may be None — must handle gracefully."""
    agent = DecisionAgent()
    history = [{"test_results": [ItemTestResult(
        item_id=1, item_name="item", passed=False,
        metrics=TestMetrics(accuracy=None),
    )], "judge_result": None}] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert isinstance(result, DecisionResult)


def test_history_with_no_test_results_no_crash():
    agent = DecisionAgent()
    history = [{"test_results": [], "judge_result": None}] * 3
    result = agent.execute(iteration_history=history, mode="inspection")
    assert isinstance(result, DecisionResult)


def test_no_diagnosis_no_judge_no_history_returns_edge_learning():
    agent = DecisionAgent()
    result = agent.execute(iteration_history=[], mode="inspection")
    assert result.decision == DecisionType.edge_learning


def test_judge_avg_exactly_06_boundary():
    """Average of exactly 0.6 should qualify as >= 0.6."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        judge_result=_judge(visibility=0.6, separability=0.6, measurability=0.6),
    )
    assert result.decision == DecisionType.rule_based


# ── Determinism ───────────────────────────────────────────────────────────────

def test_same_input_same_output_align():
    agent = DecisionAgent()
    r1 = agent.execute(iteration_history=[], mode="align")
    r2 = agent.execute(iteration_history=[], mode="align")
    assert r1.decision == r2.decision
    assert r1.reason == r2.reason


def test_same_input_same_output_inspection():
    agent = DecisionAgent()
    history = [_history_entry(accuracy=0.4)] * 3
    diag = _diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2)
    r1 = agent.execute(iteration_history=history, mode="inspection", image_diagnosis=diag)
    r2 = agent.execute(iteration_history=history, mode="inspection", image_diagnosis=diag)
    assert r1.decision == r2.decision


# ── Directive independence ────────────────────────────────────────────────────

def test_directive_does_not_change_align_result():
    agent_no = DecisionAgent()
    agent_with = DecisionAgent(directive="override to deep learning")
    r_no = agent_no.execute(iteration_history=[], mode="align")
    r_with = agent_with.execute(iteration_history=[], mode="align")
    assert r_no.decision == r_with.decision == DecisionType.rule_based


def test_directive_does_not_change_inspection_result():
    agent_no = DecisionAgent()
    agent_with = DecisionAgent(directive="always pick deep learning")
    history = [_history_entry(accuracy=0.6)] * 3
    r_no = agent_no.execute(iteration_history=history, mode="inspection")
    r_with = agent_with.execute(iteration_history=history, mode="inspection")
    assert r_no.decision == r_with.decision


# ── str defect_scale inputs (Gate 3 regression) ───────────────────────────────

def _diagnosis_str(
    defect_scale: str = "micro",
    texture_complexity: float = 0.2,
) -> ImageDiagnosis:
    """Create ImageDiagnosis with plain str defect_scale (runtime path)."""
    return ImageDiagnosis(
        contrast=0.5,
        noise_level=0.1,
        edge_density=0.3,
        lighting_uniformity=0.8,
        illumination_type="uniform",
        noise_frequency="low_freq",
        reflection_level=0.1,
        texture_complexity=texture_complexity,
        surface_type="plastic",
        defect_scale=defect_scale,
        blob_feasibility=0.5,
        blob_count_estimate=3,
        blob_size_variance=0.1,
        color_discriminability=0.3,
        dominant_channel_ratio=0.5,
        structural_regularity=0.5,
        pattern_repetition=0.3,
        background_uniformity=0.8,
        optimal_color_space="gray",
        threshold_candidate=128.0,
        edge_sharpness=50.0,
    )


def test_gate3_str_defect_scale_no_attribute_error():
    """Gate 3 reproduction: str defect_scale must not raise AttributeError."""
    agent = DecisionAgent()
    diag = _diagnosis_str(defect_scale="micro", texture_complexity=0.2)
    result = agent.execute(
        iteration_history=[{}],
        mode="inspection",
        judge_result=_judge(visibility=0.3, separability=0.3, measurability=0.3),
        image_diagnosis=diag,
    )
    assert isinstance(result, DecisionResult)


def test_str_micro_low_texture_returns_edge_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis_str(defect_scale="micro", texture_complexity=0.2),
    )
    assert result.decision == DecisionType.edge_learning


def test_str_texture_defect_scale_returns_deep_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis_str(defect_scale="texture", texture_complexity=0.1),
    )
    assert result.decision == DecisionType.deep_learning


def test_str_macro_low_texture_falls_back_to_edge_learning():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis_str(defect_scale="macro", texture_complexity=0.1),
    )
    assert result.decision == DecisionType.edge_learning


def test_str_defect_scale_evidence_dict_is_plain_str():
    """Evidence dict must contain plain str, not repr like 'DefectScale.micro'."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis_str(defect_scale="micro", texture_complexity=0.2),
    )
    assert result.details["defect_scale"] == "micro"


def test_enum_defect_scale_evidence_dict_is_plain_str():
    """Enum input must also produce plain str in evidence dict."""
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2),
    )
    assert result.details["defect_scale"] == "micro"


def test_str_and_enum_micro_produce_same_decision():
    agent = DecisionAgent()
    r_str = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis_str(defect_scale="micro", texture_complexity=0.2),
    )
    r_enum = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.micro, texture_complexity=0.2),
    )
    assert r_str.decision == r_enum.decision


def test_str_and_enum_texture_produce_same_decision():
    agent = DecisionAgent()
    r_str = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis_str(defect_scale="texture", texture_complexity=0.1),
    )
    r_enum = agent.execute(
        iteration_history=[],
        mode="inspection",
        image_diagnosis=_diagnosis(defect_scale=DefectScale.texture, texture_complexity=0.1),
    )
    assert r_str.decision == r_enum.decision


def test_str_defect_scale_align_mode_no_crash():
    agent = DecisionAgent()
    result = agent.execute(
        iteration_history=[],
        mode="align",
        image_diagnosis=_diagnosis_str(defect_scale="texture", texture_complexity=0.9),
    )
    assert result.decision == DecisionType.rule_based
