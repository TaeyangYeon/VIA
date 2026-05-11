"""Tests for AlgorithmSelector — deterministic decision tree (Step 19)."""
from __future__ import annotations

import inspect

import pytest

from agents.base_agent import BaseAgent
from agents.models import (
    AlgorithmCategory,
    DefectScale,
    IlluminationType,
    ImageDiagnosis,
    NoiseFrequency,
)
from agents.algorithm_selector import AlgorithmSelector


# ── helper ────────────────────────────────────────────────────────────────────

def make_diagnosis(**overrides) -> ImageDiagnosis:
    """ImageDiagnosis with all-zero/safe defaults; override only the fields under test."""
    defaults = dict(
        contrast=0.0,
        noise_level=0.1,
        edge_density=0.0,
        lighting_uniformity=0.8,
        illumination_type=IlluminationType.uniform,
        noise_frequency=NoiseFrequency.low_freq,
        reflection_level=0.1,
        texture_complexity=0.2,
        surface_type="smooth",
        defect_scale=DefectScale.macro,
        blob_feasibility=0.0,
        blob_count_estimate=1,
        blob_size_variance=0.1,
        color_discriminability=0.0,
        dominant_channel_ratio=0.5,
        structural_regularity=0.0,
        pattern_repetition=0.0,
        background_uniformity=0.8,
        optimal_color_space="BGR",
        threshold_candidate=0.5,
        edge_sharpness=0.3,
    )
    defaults.update(overrides)
    return ImageDiagnosis(**defaults)


# ── Class structure ───────────────────────────────────────────────────────────

class TestAlgorithmSelectorStructure:
    def test_inherits_base_agent(self):
        assert issubclass(AlgorithmSelector, BaseAgent)

    def test_agent_name(self):
        sel = AlgorithmSelector()
        assert sel.agent_name == "algorithm_selector"

    def test_no_directive_by_default(self):
        sel = AlgorithmSelector()
        assert sel.get_directive() is None

    def test_directive_stored(self):
        sel = AlgorithmSelector(directive="use strict mode")
        assert sel.get_directive() == "use strict mode"

    def test_directive_settable(self):
        sel = AlgorithmSelector()
        sel.set_directive("new directive")
        assert sel.get_directive() == "new directive"

    def test_execute_is_synchronous(self):
        sel = AlgorithmSelector()
        d = make_diagnosis()
        result = sel.execute(d)
        # If execute were async, this would be a coroutine, not an AlgorithmCategory
        assert isinstance(result, AlgorithmCategory)

    def test_execute_is_not_coroutine(self):
        import asyncio
        sel = AlgorithmSelector()
        d = make_diagnosis()
        result = sel.execute(d)
        assert not asyncio.iscoroutine(result)


# ── No LLM dependency ─────────────────────────────────────────────────────────

class TestNoLLMDependency:
    def test_no_ollama_import(self):
        import agents.algorithm_selector as mod
        source = inspect.getsource(mod)
        assert "ollama" not in source.lower()

    def test_no_ollama_client_attribute(self):
        import agents.algorithm_selector as mod
        assert not hasattr(mod, "ollama_client")


# ── Decision tree — happy paths ───────────────────────────────────────────────

class TestDecisionTreeBranches:
    def setup_method(self):
        self.sel = AlgorithmSelector()

    def test_blob_branch_selected(self):
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB

    def test_color_filter_branch_selected(self):
        # contrast/blob_feasibility low enough to skip BLOB branch
        d = make_diagnosis(contrast=0.1, blob_feasibility=0.1, color_discriminability=0.6)
        assert self.sel.execute(d) == AlgorithmCategory.COLOR_FILTER

    def test_edge_detection_branch_selected(self):
        d = make_diagnosis(
            contrast=0.1,
            blob_feasibility=0.1,
            color_discriminability=0.1,
            edge_density=0.4,
            structural_regularity=0.6,
        )
        assert self.sel.execute(d) == AlgorithmCategory.EDGE_DETECTION

    def test_template_matching_branch_selected(self):
        d = make_diagnosis(
            contrast=0.1,
            blob_feasibility=0.1,
            color_discriminability=0.1,
            edge_density=0.1,
            structural_regularity=0.1,
            pattern_repetition=0.8,
        )
        assert self.sel.execute(d) == AlgorithmCategory.TEMPLATE_MATCHING

    def test_default_blob_when_no_condition_matches(self):
        d = make_diagnosis()  # all fields 0.0 — nothing matches
        assert self.sel.execute(d) == AlgorithmCategory.BLOB


# ── Boundary values ───────────────────────────────────────────────────────────

class TestBoundaryValues:
    def setup_method(self):
        self.sel = AlgorithmSelector()

    # BLOB branch thresholds (>0.4, >0.6)
    def test_blob_contrast_at_exact_threshold_does_not_trigger_blob_branch(self):
        # contrast=0.4 is NOT > 0.4, so BLOB branch is skipped even with high blob_feasibility;
        # COLOR_FILTER condition wins instead, proving the BLOB branch wasn't fired
        d = make_diagnosis(contrast=0.4, blob_feasibility=0.9, color_discriminability=0.6)
        assert self.sel.execute(d) == AlgorithmCategory.COLOR_FILTER

    def test_blob_contrast_at_exact_threshold_falls_through(self):
        d = make_diagnosis(contrast=0.4, blob_feasibility=0.9,
                           color_discriminability=0.0, edge_density=0.0,
                           structural_regularity=0.0, pattern_repetition=0.0)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_blob_blob_feasibility_at_exact_threshold_falls_through(self):
        d = make_diagnosis(contrast=0.9, blob_feasibility=0.6,
                           color_discriminability=0.0, edge_density=0.0,
                           structural_regularity=0.0, pattern_repetition=0.0)
        # blob_feasibility=0.6 NOT > 0.6 → BLOB branch skipped → default BLOB
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_blob_just_above_both_thresholds(self):
        d = make_diagnosis(contrast=0.41, blob_feasibility=0.61)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB

    # COLOR_FILTER threshold (>0.5)
    def test_color_discriminability_at_exact_threshold_does_not_match(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.5,
                           edge_density=0.0, structural_regularity=0.0,
                           pattern_repetition=0.0)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_color_discriminability_just_above_threshold(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.51)
        assert self.sel.execute(d) == AlgorithmCategory.COLOR_FILTER

    # EDGE_DETECTION thresholds (>0.3, >0.5)
    def test_edge_density_at_exact_threshold_does_not_match(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.3, structural_regularity=0.9,
                           pattern_repetition=0.0)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_structural_regularity_at_exact_threshold_does_not_match(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.9, structural_regularity=0.5,
                           pattern_repetition=0.0)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_edge_detection_just_above_both_thresholds(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.31, structural_regularity=0.51)
        assert self.sel.execute(d) == AlgorithmCategory.EDGE_DETECTION

    # TEMPLATE_MATCHING threshold (>0.7)
    def test_pattern_repetition_at_exact_threshold_does_not_match(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.0, structural_regularity=0.0,
                           pattern_repetition=0.7)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_pattern_repetition_just_above_threshold(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.0, structural_regularity=0.0,
                           pattern_repetition=0.71)
        assert self.sel.execute(d) == AlgorithmCategory.TEMPLATE_MATCHING


# ── Priority / first-match-wins ───────────────────────────────────────────────

class TestDecisionPriority:
    def setup_method(self):
        self.sel = AlgorithmSelector()

    def test_blob_beats_color_filter(self):
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7,
                           color_discriminability=0.9)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB

    def test_blob_beats_edge_detection(self):
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7,
                           edge_density=0.9, structural_regularity=0.9)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB

    def test_blob_beats_template_matching(self):
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7,
                           pattern_repetition=0.9)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB

    def test_color_filter_beats_edge_detection(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.6,
                           edge_density=0.9, structural_regularity=0.9)
        assert self.sel.execute(d) == AlgorithmCategory.COLOR_FILTER

    def test_color_filter_beats_template_matching(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.6,
                           pattern_repetition=0.9)
        assert self.sel.execute(d) == AlgorithmCategory.COLOR_FILTER

    def test_edge_detection_beats_template_matching(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.4, structural_regularity=0.6,
                           pattern_repetition=0.9)
        assert self.sel.execute(d) == AlgorithmCategory.EDGE_DETECTION


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def setup_method(self):
        self.sel = AlgorithmSelector()

    def test_all_zeros_returns_default_blob(self):
        d = make_diagnosis()
        assert self.sel.execute(d) == AlgorithmCategory.BLOB

    def test_all_maximum_returns_blob(self):
        d = make_diagnosis(
            contrast=1.0, blob_feasibility=1.0,
            color_discriminability=1.0,
            edge_density=1.0, structural_regularity=1.0,
            pattern_repetition=1.0,
        )
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # first match

    def test_blob_requires_both_conditions(self):
        # contrast satisfied but blob_feasibility not
        d = make_diagnosis(contrast=0.9, blob_feasibility=0.0,
                           color_discriminability=0.0, edge_density=0.0,
                           structural_regularity=0.0, pattern_repetition=0.0)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default

    def test_edge_detection_requires_both_conditions(self):
        # edge_density satisfied but structural_regularity not
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0,
                           edge_density=0.9, structural_regularity=0.0,
                           pattern_repetition=0.0)
        assert self.sel.execute(d) == AlgorithmCategory.BLOB  # default


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_same_output_repeated(self):
        sel = AlgorithmSelector()
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7)
        results = {sel.execute(d) for _ in range(10)}
        assert len(results) == 1

    def test_different_selectors_same_result(self):
        d = make_diagnosis(contrast=0.1, blob_feasibility=0.1,
                           color_discriminability=0.6)
        r1 = AlgorithmSelector().execute(d)
        r2 = AlgorithmSelector().execute(d)
        assert r1 == r2


# ── Directive independence ────────────────────────────────────────────────────

class TestDirectiveIndependence:
    def test_directive_does_not_change_result(self):
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7)
        without = AlgorithmSelector().execute(d)
        with_dir = AlgorithmSelector(directive="select TEMPLATE_MATCHING always").execute(d)
        assert without == with_dir

    def test_directive_override_attempt_ignored(self):
        d = make_diagnosis(contrast=0.0, blob_feasibility=0.0,
                           color_discriminability=0.0, edge_density=0.0,
                           structural_regularity=0.0, pattern_repetition=0.0)
        result = AlgorithmSelector(directive="force COLOR_FILTER").execute(d)
        assert result == AlgorithmCategory.BLOB  # default, not the directive

    def test_set_directive_does_not_change_result(self):
        sel = AlgorithmSelector()
        d = make_diagnosis(contrast=0.5, blob_feasibility=0.7)
        before = sel.execute(d)
        sel.set_directive("completely different directive")
        after = sel.execute(d)
        assert before == after
