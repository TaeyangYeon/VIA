"""Vision judge agent for multimodal image quality assessment via Gemma4."""
from __future__ import annotations

import base64
import json
import re
from typing import Optional

import cv2
import numpy as np

from agents.base_agent import BaseAgent
from agents.models import JudgementResult
from agents.prompts.vision_judge_prompt import (
    VISION_JUDGE_SYSTEM_PROMPT,
    build_vision_judge_prompt,
)
from backend.services.ollama_client import OllamaError, ollama_client


def _encode_image(image: np.ndarray) -> str:
    success, buf = cv2.imencode(".png", image)
    if not success:
        raise ValueError("Failed to encode image as PNG")
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_response(text: str) -> JudgementResult:
    cleaned = _strip_fences(text)
    data = json.loads(cleaned)
    return JudgementResult(
        visibility_score=_clamp(float(data["visibility_score"])),
        separability_score=_clamp(float(data["separability_score"])),
        measurability_score=_clamp(float(data["measurability_score"])),
        problems=list(data.get("problems", [])),
        next_suggestion=str(data.get("next_suggestion", "")),
    )


class VisionJudgeAgent(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("vision_judge", directive)

    async def execute(
        self,
        original_image: np.ndarray,
        processed_image: np.ndarray,
        purpose: str,
        pipeline_name: str,
    ) -> JudgementResult:
        prompt = build_vision_judge_prompt(
            purpose=purpose,
            pipeline_name=pipeline_name,
            directive=self.get_directive(),
        )
        images = [_encode_image(original_image), _encode_image(processed_image)]

        for attempt in range(2):
            try:
                response = await ollama_client.generate_with_images(
                    prompt, images, system=VISION_JUDGE_SYSTEM_PROMPT
                )
                if not response:
                    raise ValueError("Empty response from Ollama")
                result = _parse_response(response)
                self._log("INFO", f"Judgement complete for pipeline '{pipeline_name}'")
                return result
            except OllamaError:
                raise
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                if attempt == 1:
                    self._log("ERROR", f"Failed to parse Ollama response after retry: {exc}")
                    raise ValueError(
                        f"VisionJudgeAgent: unparseable response after 2 attempts — {exc}"
                    ) from exc
