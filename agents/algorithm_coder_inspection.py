"""Algorithm coder agent for generating inspection mode OpenCV code."""
import json
import re
from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import AlgorithmCategory, AlgorithmResult, InspectionPlan, ProcessingPipeline
from agents.prompts.coder_inspection_prompt import (
    CODER_INSPECTION_SYSTEM_PROMPT,
    build_coder_inspection_prompt,
)
from backend.services.ollama_client import OllamaClient, OllamaError, ollama_client as _default_client


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


class AlgorithmCoderInspection(BaseAgent):
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        directive: Optional[str] = None,
    ) -> None:
        super().__init__("algorithm_coder_inspection", directive)
        self._ollama = ollama_client if ollama_client is not None else _default_client

    async def execute(
        self,
        category: AlgorithmCategory,
        pipeline: ProcessingPipeline,
        plan: InspectionPlan,
    ) -> AlgorithmResult:
        pipeline_summary = ", ".join(
            f"{b.name}({b.params})" if b.params else b.name
            for b in pipeline.blocks
        ) if pipeline.blocks else "(no preprocessing)"

        codes = []
        explanations = []

        for item in plan.items:
            prompt = build_coder_inspection_prompt(
                item=item,
                category=category,
                pipeline_summary=pipeline_summary,
                directive=self.get_directive(),
            )
            parsed = await self._generate_with_retry(prompt, item.name)
            codes.append(parsed["code"])
            explanations.append(f"[{item.name}] {parsed['explanation']}")

        combined_code = "\n\n".join(codes)
        combined_explanation = "\n".join(explanations)

        self._log("INFO", f"{len(plan.items)}개 항목 코드 생성 완료")
        return AlgorithmResult(
            code=combined_code,
            explanation=combined_explanation,
            category=category,
            pipeline=pipeline,
        )

    async def _generate_with_retry(self, prompt: str, item_name: str) -> dict:
        for attempt in range(2):
            raw = await self._ollama.generate(prompt, system=CODER_INSPECTION_SYSTEM_PROMPT)
            if not raw or not raw.strip():
                if attempt == 0:
                    continue
                raise ValueError(f"Empty response for item '{item_name}' after retry")
            try:
                return _parse_json_response(raw)
            except (json.JSONDecodeError, ValueError):
                if attempt == 0:
                    continue
                self._log("ERROR", f"JSON 파싱 실패: {item_name}")
                raise ValueError(f"Failed to parse JSON response for item '{item_name}' after retry")
        raise ValueError(f"Unexpected retry exhaustion for item '{item_name}'")
