"""Algorithm coder agent for generating align mode coordinate detection code."""
import json
import re
from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import AlgorithmCategory, AlgorithmResult, ProcessingPipeline
from agents.prompts.coder_align_prompt import (
    CODER_ALIGN_SYSTEM_PROMPT,
    build_coder_align_prompt,
)
from backend.services.ollama_client import OllamaClient, OllamaError, ollama_client as _default_client


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


class AlgorithmCoderAlign(BaseAgent):
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        directive: Optional[str] = None,
    ) -> None:
        super().__init__("algorithm_coder_align", directive)
        self._ollama = ollama_client if ollama_client is not None else _default_client

    async def execute(self, pipeline: ProcessingPipeline) -> AlgorithmResult:
        pipeline_summary = (
            ", ".join(
                f"{b.name}({b.params})" if b.params else b.name
                for b in pipeline.blocks
            )
            if pipeline.blocks
            else "(no preprocessing)"
        )

        prompt = build_coder_align_prompt(
            pipeline_summary=pipeline_summary,
            directive=self.get_directive(),
        )
        parsed = await self._generate_with_retry(prompt)

        self._log("INFO", "Align 코드 생성 완료")
        return AlgorithmResult(
            code=parsed["code"],
            explanation=parsed["explanation"],
            category=AlgorithmCategory.TEMPLATE_MATCHING,
            pipeline=pipeline,
        )

    async def _generate_with_retry(self, prompt: str) -> dict:
        for attempt in range(2):
            raw = await self._ollama.generate(prompt, system=CODER_ALIGN_SYSTEM_PROMPT)
            if not raw or not raw.strip():
                if attempt == 0:
                    continue
                raise ValueError("Empty response after retry")
            try:
                return _parse_json_response(raw)
            except (json.JSONDecodeError, ValueError):
                if attempt == 0:
                    continue
                self._log("ERROR", "JSON 파싱 실패 (align)")
                raise ValueError("Failed to parse JSON response after retry")
        raise ValueError("Unexpected retry exhaustion")
