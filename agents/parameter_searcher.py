"""Parameter searcher for automatic pipeline parameter optimization."""
from __future__ import annotations

import itertools
import random
from typing import Optional

import numpy as np

from agents.base_agent import BaseAgent
from agents.models import ProcessingPipeline
from agents.pipeline_blocks import block_library
from agents.processing_quality_evaluator import ProcessingQualityEvaluator

_MAX_COMBOS = 500


class ParameterSearcher(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("parameter_searcher", directive)
        self._evaluator = ProcessingQualityEvaluator()

    def execute(self, pipeline: ProcessingPipeline, image: np.ndarray) -> ProcessingPipeline:
        directive = self.get_directive()
        if directive:
            self._log("INFO", "Agent directive active", {"directive": directive})

        current_image = image.copy()

        for block in pipeline.blocks:
            block_def = block_library.get_block(block.name)
            search_space = block_def.params

            if not search_space:
                continue

            param_names = list(search_space.keys())
            param_values = [search_space[k] for k in param_names]
            all_combos = list(itertools.product(*param_values))

            if len(all_combos) > _MAX_COMBOS:
                rng = random.Random(42)
                all_combos = rng.sample(all_combos, _MAX_COMBOS)

            best_score = -1.0
            best_params: Optional[dict] = None

            for combo in all_combos:
                params = dict(zip(param_names, combo))
                try:
                    result_image = block_def.apply(current_image, params)
                    metrics = self._evaluator.evaluate(current_image, result_image)
                    score = metrics["overall_score"]
                    if score > best_score:
                        best_score = score
                        best_params = params
                except Exception as e:
                    self._log("WARNING", f"Param combo failed for block '{block.name}'", {
                        "params": str(params), "error": str(e),
                    })

            if best_params is None:
                self._log("ERROR", f"All param combinations failed for block '{block.name}'", {
                    "block": block.name,
                })
                block.params = {}
            else:
                block.params = best_params
                try:
                    current_image = block_def.apply(current_image, best_params)
                except Exception as e:
                    self._log("WARNING", f"Failed to apply best params for '{block.name}'", {
                        "error": str(e),
                    })

        # Final end-to-end evaluation
        final_image = image.copy()
        for block in pipeline.blocks:
            block_def = block_library.get_block(block.name)
            params = block.params if block.params else {}
            try:
                final_image = block_def.apply(final_image, params)
            except Exception as e:
                self._log("WARNING", f"Final pipeline eval failed at '{block.name}'", {
                    "error": str(e),
                })

        final_metrics = self._evaluator.evaluate(image, final_image)
        pipeline.score = final_metrics["overall_score"]

        return pipeline
