"""Algorithm selector using Python decision tree for category determination."""
from __future__ import annotations

from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import AlgorithmCategory, ImageDiagnosis


class AlgorithmSelector(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("algorithm_selector", directive)

    def execute(self, diagnosis: ImageDiagnosis) -> AlgorithmCategory:  # type: ignore[override]
        if self._directive:
            self._log("INFO", f"Directive received (ignored by decision tree): {self._directive}")

        if diagnosis.contrast > 0.4 and diagnosis.blob_feasibility > 0.6:
            result = AlgorithmCategory.BLOB
            reason = "contrast > 0.4 and blob_feasibility > 0.6"
        elif diagnosis.color_discriminability > 0.5:
            result = AlgorithmCategory.COLOR_FILTER
            reason = "color_discriminability > 0.5"
        elif diagnosis.edge_density > 0.3 and diagnosis.structural_regularity > 0.5:
            result = AlgorithmCategory.EDGE_DETECTION
            reason = "edge_density > 0.3 and structural_regularity > 0.5"
        elif diagnosis.pattern_repetition > 0.7:
            result = AlgorithmCategory.TEMPLATE_MATCHING
            reason = "pattern_repetition > 0.7"
        else:
            result = AlgorithmCategory.BLOB
            reason = "default fallback"

        self._log("INFO", f"Selected {result.value}: {reason}")
        return result
