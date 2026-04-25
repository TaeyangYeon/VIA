"""Tests for Pipeline Composer (Step 15)."""
import inspect

import pytest

from agents.base_agent import BaseAgent
from agents.models import (
    DefectScale,
    IlluminationType,
    ImageDiagnosis,
    NoiseFrequency,
    PipelineBlock,
    ProcessingPipeline,
)
from agents.pipeline_blocks import block_library
from agents.pipeline_composer import PipelineComposer


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


CATEGORY_ORDER = ["color_space", "noise_reduction", "threshold", "morphology", "edge"]


def block_category(block_name: str) -> str:
    return block_library.get_block(block_name).category


def category_index(cat: str) -> int:
    return CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else len(CATEGORY_ORDER)


def pipeline_by_name(pipelines: list[ProcessingPipeline], name: str) -> ProcessingPipeline:
    return next(p for p in pipelines if p.name == name)


# ── Section 1: Class Structure ────────────────────────────────────────────────

class TestClassStructure:
    def test_inherits_base_agent(self):
        assert issubclass(PipelineComposer, BaseAgent)

    def test_agent_name(self):
        assert PipelineComposer().agent_name == "pipeline_composer"

    def test_execute_is_callable_and_synchronous(self):
        result = PipelineComposer().execute(make_diagnosis())
        assert not inspect.iscoroutine(result)
        assert isinstance(result, list)

    def test_constructor_accepts_directive(self):
        composer = PipelineComposer(directive="Blob 우선")
        assert composer.get_directive() == "Blob 우선"

    def test_directive_stored_and_retrievable_via_set(self):
        composer = PipelineComposer()
        assert composer.get_directive() is None
        composer.set_directive("새 지시")
        assert composer.get_directive() == "새 지시"


# ── Section 2: Output Validation ──────────────────────────────────────────────

class TestOutputValidation:
    def setup_method(self):
        self.pipelines = PipelineComposer().execute(make_diagnosis())

    def test_returns_list_of_processing_pipelines(self):
        assert isinstance(self.pipelines, list)
        for p in self.pipelines:
            assert isinstance(p, ProcessingPipeline)

    def test_generates_exactly_5_pipelines(self):
        assert len(self.pipelines) == 5

    def test_exactly_5_across_diagnoses(self):
        for d in [
            make_diagnosis(noise_level=0.9),
            make_diagnosis(contrast=0.1),
            make_diagnosis(illumination_type=IlluminationType.uneven),
        ]:
            assert len(PipelineComposer().execute(d)) == 5

    def test_all_pipeline_names_nonempty_and_unique(self):
        names = [p.name for p in self.pipelines]
        assert all(len(n.strip()) > 0 for n in names)
        assert len(names) == len(set(names))

    def test_all_scores_zero(self):
        assert all(p.score == 0.0 for p in self.pipelines)

    def test_each_pipeline_has_at_least_one_block(self):
        for p in self.pipelines:
            assert len(p.blocks) >= 1, f"'{p.name}' has no blocks"


# ── Section 3: PipelineBlock Field Validation ─────────────────────────────────

class TestPipelineBlockFields:
    def setup_method(self):
        self.pipelines = PipelineComposer().execute(make_diagnosis())

    def test_all_block_params_are_empty_dict(self):
        for p in self.pipelines:
            for b in p.blocks:
                assert b.params == {}, \
                    f"'{b.name}' in '{p.name}' has params={b.params!r}"

    def test_all_block_names_are_nonempty_strings(self):
        for p in self.pipelines:
            for b in p.blocks:
                assert isinstance(b.name, str) and len(b.name) > 0

    def test_all_block_when_conditions_are_nonempty_strings(self):
        for p in self.pipelines:
            for b in p.blocks:
                assert isinstance(b.when_condition, str) and len(b.when_condition) > 0, \
                    f"'{b.name}' in '{p.name}' has empty when_condition"


# ── Section 4: Block Constraints ──────────────────────────────────────────────

class TestBlockConstraints:
    def setup_method(self):
        self.pipelines = PipelineComposer().execute(make_diagnosis())

    def test_all_block_names_exist_in_library(self):
        all_names = {bd.name for bd in block_library.get_all_blocks()}
        for p in self.pipelines:
            for b in p.blocks:
                assert b.name in all_names, f"'{b.name}' not found in block_library"

    def test_max_1_color_space_per_pipeline(self):
        for p in self.pipelines:
            count = sum(1 for b in p.blocks if block_category(b.name) == "color_space")
            assert count <= 1, f"'{p.name}' has {count} color_space blocks"

    def test_max_2_noise_reduction_per_pipeline(self):
        for p in self.pipelines:
            count = sum(1 for b in p.blocks if block_category(b.name) == "noise_reduction")
            assert count <= 2, f"'{p.name}' has {count} noise_reduction blocks"

    def test_max_1_threshold_per_pipeline(self):
        for p in self.pipelines:
            count = sum(1 for b in p.blocks if block_category(b.name) == "threshold")
            assert count <= 1, f"'{p.name}' has {count} threshold blocks"

    def test_max_2_morphology_per_pipeline(self):
        for p in self.pipelines:
            count = sum(1 for b in p.blocks if block_category(b.name) == "morphology")
            assert count <= 2, f"'{p.name}' has {count} morphology blocks"

    def test_max_1_edge_per_pipeline(self):
        for p in self.pipelines:
            count = sum(1 for b in p.blocks if block_category(b.name) == "edge")
            assert count <= 1, f"'{p.name}' has {count} edge blocks"

    def test_no_duplicate_blocks_within_pipeline(self):
        for p in self.pipelines:
            names = [b.name for b in p.blocks]
            assert len(names) == len(set(names)), \
                f"Duplicate blocks in '{p.name}': {names}"


# ── Section 5: Block Ordering ──────────────────────────────────────────────────

class TestBlockOrdering:
    def _assert_ordered(self, pipelines: list[ProcessingPipeline], label: str) -> None:
        for p in pipelines:
            indices = [category_index(block_category(b.name)) for b in p.blocks]
            assert indices == sorted(indices), \
                f"[{label}] '{p.name}' out-of-order: {[b.name for b in p.blocks]}"

    def test_ordering_with_standard_diagnosis(self):
        self._assert_ordered(
            PipelineComposer().execute(make_diagnosis()),
            "standard",
        )

    def test_ordering_with_high_noise_diagnosis(self):
        self._assert_ordered(
            PipelineComposer().execute(make_diagnosis(noise_level=0.9, contrast=0.5)),
            "high_noise",
        )

    def test_ordering_with_uneven_illumination_diagnosis(self):
        self._assert_ordered(
            PipelineComposer().execute(
                make_diagnosis(illumination_type=IlluminationType.uneven, contrast=0.5)
            ),
            "uneven_illumination",
        )


# ── Section 6: Pipeline Diversity ─────────────────────────────────────────────

class TestPipelineDiversity:
    def setup_method(self):
        self.pipelines = PipelineComposer().execute(make_diagnosis())

    def test_not_all_pipelines_identical(self):
        block_sets = [frozenset(b.name for b in p.blocks) for p in self.pipelines]
        assert len(set(block_sets)) > 1, "All pipelines have identical block sets"

    def test_at_least_one_pipeline_has_edge_block(self):
        has_edge = any(
            any(block_category(b.name) == "edge" for b in p.blocks)
            for p in self.pipelines
        )
        assert has_edge, "No pipeline contains an edge block"

    def test_at_least_one_pipeline_has_morphology_blocks(self):
        has_morph = any(
            any(block_category(b.name) == "morphology" for b in p.blocks)
            for p in self.pipelines
        )
        assert has_morph, "No pipeline contains morphology blocks"


# ── Section 7: Edge Cases ──────────────────────────────────────────────────────

class TestEdgeCases:
    def test_high_noise_produces_5_valid_pipelines(self):
        d = make_diagnosis(noise_level=0.9, contrast=0.5)
        pipelines = PipelineComposer().execute(d)
        assert len(pipelines) == 5
        has_nr = any(
            any(block_category(b.name) == "noise_reduction" for b in p.blocks)
            for p in pipelines
        )
        assert has_nr, "High-noise: no noise_reduction blocks found"

    def test_low_contrast_produces_5_valid_pipelines(self):
        d = make_diagnosis(contrast=0.1, noise_level=0.3)
        pipelines = PipelineComposer().execute(d)
        assert len(pipelines) == 5
        for p in pipelines:
            assert len(p.blocks) >= 1

    def test_minimal_matching_diagnosis_produces_5_pipelines(self):
        d = make_diagnosis(
            contrast=0.0,
            noise_level=0.0,
            color_discriminability=0.35,
            illumination_type=IlluminationType.uniform,
            reflection_level=0.0,
            blob_feasibility=0.0,
            defect_scale=DefectScale.macro,
            structural_regularity=0.0,
            surface_type="plastic",
        )
        pipelines = PipelineComposer().execute(d)
        assert len(pipelines) == 5

    def test_uniform_high_contrast_produces_5_pipelines(self):
        d = make_diagnosis(
            contrast=0.9,
            noise_level=0.05,
            illumination_type=IlluminationType.uniform,
        )
        pipelines = PipelineComposer().execute(d)
        assert len(pipelines) == 5


# ── Section 8: Directive Support ──────────────────────────────────────────────

class TestDirectiveSupport:
    def _diagnosis_with_morphology(self) -> ImageDiagnosis:
        # noise_level=0.3 → erosion/opening match; blob_feasibility=0.5 → dilation/closing match
        return make_diagnosis(noise_level=0.3, blob_feasibility=0.5, contrast=0.5)

    def test_blob_uppercase_moves_morphology_pipeline_first(self):
        d = self._diagnosis_with_morphology()
        pipelines = PipelineComposer(directive="Blob 방식 파이프라인 우선 시도").execute(d)
        first_pipeline = pipelines[0]
        has_morph = any(block_category(b.name) == "morphology" for b in first_pipeline.blocks)
        assert has_morph, f"First pipeline '{first_pipeline.name}' has no morphology blocks"

    def test_blob_lowercase_moves_morphology_pipeline_first(self):
        d = self._diagnosis_with_morphology()
        pipelines = PipelineComposer(directive="blob 방식으로 검출").execute(d)
        first_pipeline = pipelines[0]
        has_morph = any(block_category(b.name) == "morphology" for b in first_pipeline.blocks)
        assert has_morph, f"First pipeline '{first_pipeline.name}' has no morphology blocks (blob lowercase)"

    def test_blobl_korean_moves_morphology_pipeline_first(self):
        d = self._diagnosis_with_morphology()
        pipelines = PipelineComposer(directive="블롭 기반 결함 검출 시도").execute(d)
        first_pipeline = pipelines[0]
        has_morph = any(block_category(b.name) == "morphology" for b in first_pipeline.blocks)
        assert has_morph, f"First pipeline '{first_pipeline.name}' has no morphology blocks (블롭)"

    def test_directive_does_not_violate_count_or_uniqueness(self):
        d = make_diagnosis()
        pipelines = PipelineComposer(directive="Blob 우선, 모든 전략 시도").execute(d)
        assert len(pipelines) == 5
        names = [p.name for p in pipelines]
        assert len(names) == len(set(names))


# ── Section 9: Strategy-specific Tests ────────────────────────────────────────

class TestStrategySpecific:
    def test_aggressive_denoising_has_color_space_and_two_nr_blocks(self):
        """noise_level=0.8 → median + nlmeans both match → aggressive strategy gets 2 NR blocks."""
        d = make_diagnosis(noise_level=0.8, contrast=0.5)
        pipelines = PipelineComposer().execute(d)
        p = pipeline_by_name(pipelines, "적극적_노이즈제거_파이프라인")
        categories = [block_category(b.name) for b in p.blocks]
        assert "color_space" in categories, "적극적 strategy missing color_space block"
        nr_count = categories.count("noise_reduction")
        assert nr_count == 2, f"적극적 strategy should have 2 NR blocks, got {nr_count}: {[b.name for b in p.blocks]}"

    def test_adaptive_threshold_prefers_adaptive_over_otsu(self):
        """Uneven illumination makes adaptive_mean/gauss match → strategy 2 picks one."""
        d = make_diagnosis(illumination_type=IlluminationType.uneven, contrast=0.5, noise_level=0.3)
        pipelines = PipelineComposer().execute(d)
        p = pipeline_by_name(pipelines, "적응형_임계값_파이프라인")
        threshold_blocks = [b for b in p.blocks if block_category(b.name) == "threshold"]
        assert len(threshold_blocks) == 1
        assert threshold_blocks[0].name in ("adaptive_mean", "adaptive_gauss"), \
            f"적응형 strategy should use adaptive threshold, got '{threshold_blocks[0].name}'"

    def test_edge_focused_has_edge_block_and_no_threshold(self):
        d = make_diagnosis(contrast=0.5, noise_level=0.3)
        pipelines = PipelineComposer().execute(d)
        p = pipeline_by_name(pipelines, "엣지_검출_파이프라인")
        categories = [block_category(b.name) for b in p.blocks]
        assert "edge" in categories, "엣지 strategy missing edge block"
        assert "threshold" not in categories, \
            f"엣지 strategy should have no threshold block, got: {[b.name for b in p.blocks]}"

    def test_minimal_has_exactly_one_block(self):
        d = make_diagnosis(contrast=0.5)
        pipelines = PipelineComposer().execute(d)
        p = pipeline_by_name(pipelines, "최소_전처리_파이프라인")
        assert len(p.blocks) == 1, \
            f"최소 strategy should have exactly 1 block, got {len(p.blocks)}: {[b.name for b in p.blocks]}"

    def test_morphological_has_two_morphology_blocks(self):
        """noise_level=0.3 → erosion/opening match; blob_feasibility=0.5 → dilation/closing match."""
        d = make_diagnosis(noise_level=0.3, blob_feasibility=0.5, contrast=0.5)
        pipelines = PipelineComposer().execute(d)
        p = pipeline_by_name(pipelines, "형태학적_정제_파이프라인")
        mo_count = sum(1 for b in p.blocks if block_category(b.name) == "morphology")
        assert mo_count == 2, \
            f"형태학 strategy should have 2 morphology blocks, got {mo_count}: {[b.name for b in p.blocks]}"


# ── Section 10: Korean Pipeline Names ─────────────────────────────────────────

class TestKoreanPipelineNames:
    def setup_method(self):
        self.pipelines = PipelineComposer().execute(make_diagnosis())

    def test_all_5_expected_strategy_names_present(self):
        names = {p.name for p in self.pipelines}
        expected = {
            "적극적_노이즈제거_파이프라인",
            "적응형_임계값_파이프라인",
            "엣지_검출_파이프라인",
            "최소_전처리_파이프라인",
            "형태학적_정제_파이프라인",
        }
        assert names == expected, f"Unexpected pipeline names: {names}"

    def test_all_pipeline_names_contain_korean(self):
        def has_korean(text: str) -> bool:
            return any("가" <= c <= "힣" or "ㄱ" <= c <= "ㅎ" for c in text)

        for p in self.pipelines:
            assert has_korean(p.name), f"Pipeline name has no Korean: '{p.name}'"
