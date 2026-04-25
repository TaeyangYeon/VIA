"""Pipeline composer for assembling candidate processing pipelines."""
from __future__ import annotations

from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import ImageDiagnosis, PipelineBlock, ProcessingPipeline
from agents.pipeline_blocks import BlockDefinition, block_library


class PipelineComposer(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("pipeline_composer", directive)

    def execute(self, diagnosis: ImageDiagnosis) -> list[ProcessingPipeline]:
        directive = self.get_directive() or ""

        cs = block_library.get_matching_blocks(diagnosis, "color_space")
        nr = block_library.get_matching_blocks(diagnosis, "noise_reduction")
        th = block_library.get_matching_blocks(diagnosis, "threshold")
        mo = block_library.get_matching_blocks(diagnosis, "morphology")
        ed = block_library.get_matching_blocks(diagnosis, "edge")

        if not cs:
            cs = block_library.get_blocks_by_category("color_space")
        if not nr:
            nr = block_library.get_blocks_by_category("noise_reduction")
        if not th:
            th = block_library.get_blocks_by_category("threshold")
        if not mo:
            mo = block_library.get_blocks_by_category("morphology")
        if not ed:
            ed = block_library.get_blocks_by_category("edge")

        pipelines = [
            self._strategy_aggressive_denoising(cs, nr, th, mo),
            self._strategy_adaptive_threshold(nr, th, mo),
            self._strategy_edge_focused(cs, nr, ed),
            self._strategy_minimal(th),
            self._strategy_morphological(cs, nr, th, mo),
        ]

        if any(kw in directive for kw in ("Blob", "blob", "블롭")):
            pipelines.sort(key=lambda p: 0 if any(
                block_library.get_block(b.name).category == "morphology"
                for b in p.blocks
            ) else 1)

        return pipelines

    @staticmethod
    def _make_block(name: str, condition: str) -> PipelineBlock:
        return PipelineBlock(name=name, when_condition=condition, params={})

    def _strategy_aggressive_denoising(
        self,
        cs: list[BlockDefinition],
        nr: list[BlockDefinition],
        th: list[BlockDefinition],
        mo: list[BlockDefinition],
    ) -> ProcessingPipeline:
        blocks: list[PipelineBlock] = []
        blocks.append(self._make_block(cs[0].name, "색상 공간 변환"))
        for b in nr[:2]:
            blocks.append(self._make_block(b.name, "적극적 노이즈 제거"))
        if th:
            blocks.append(self._make_block(th[0].name, "이진화 임계값"))
        if mo:
            blocks.append(self._make_block(mo[0].name, "형태학적 정제"))
        return ProcessingPipeline(name="적극적_노이즈제거_파이프라인", blocks=blocks)

    def _strategy_adaptive_threshold(
        self,
        nr: list[BlockDefinition],
        th: list[BlockDefinition],
        mo: list[BlockDefinition],
    ) -> ProcessingPipeline:
        blocks: list[PipelineBlock] = []
        if nr:
            blocks.append(self._make_block(nr[0].name, "기본 노이즈 제거"))
        adaptive_th = next(
            (b for b in th if b.name in ("adaptive_mean", "adaptive_gauss")),
            th[0] if th else None,
        )
        if adaptive_th:
            blocks.append(self._make_block(adaptive_th.name, "적응형 이진화"))
        # Use second morphology block to differentiate from strategy 1
        mo_block = mo[1] if len(mo) > 1 else (mo[0] if mo else None)
        if mo_block:
            blocks.append(self._make_block(mo_block.name, "형태학적 정제"))
        return ProcessingPipeline(name="적응형_임계값_파이프라인", blocks=blocks)

    def _strategy_edge_focused(
        self,
        cs: list[BlockDefinition],
        nr: list[BlockDefinition],
        ed: list[BlockDefinition],
    ) -> ProcessingPipeline:
        blocks: list[PipelineBlock] = []
        blocks.append(self._make_block(cs[0].name, "색상 공간 변환"))
        if nr:
            blocks.append(self._make_block(nr[0].name, "노이즈 제거"))
        blocks.append(self._make_block(ed[0].name, "엣지 검출"))
        return ProcessingPipeline(name="엣지_검출_파이프라인", blocks=blocks)

    def _strategy_minimal(
        self,
        th: list[BlockDefinition],
    ) -> ProcessingPipeline:
        blocks: list[PipelineBlock] = []
        if th:
            blocks.append(self._make_block(th[0].name, "최소 전처리 이진화"))
        else:
            fallback = block_library.get_blocks_by_category("edge")
            if fallback:
                blocks.append(self._make_block(fallback[0].name, "최소 전처리 엣지"))
        return ProcessingPipeline(name="최소_전처리_파이프라인", blocks=blocks)

    def _strategy_morphological(
        self,
        cs: list[BlockDefinition],
        nr: list[BlockDefinition],
        th: list[BlockDefinition],
        mo: list[BlockDefinition],
    ) -> ProcessingPipeline:
        blocks: list[PipelineBlock] = []
        blocks.append(self._make_block(cs[0].name, "색상 공간 변환"))
        if nr:
            blocks.append(self._make_block(nr[0].name, "노이즈 제거"))
        otsu = next((b for b in th if b.name == "otsu"), th[0] if th else None)
        if otsu:
            blocks.append(self._make_block(otsu.name, "이진화 임계값"))
        for b in mo[:2]:
            blocks.append(self._make_block(b.name, "형태학적 연산"))
        return ProcessingPipeline(name="형태학적_정제_파이프라인", blocks=blocks)
