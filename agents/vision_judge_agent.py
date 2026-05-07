"""Vision judge agent for multimodal image quality assessment via Gemma4."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
from collections import OrderedDict
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
    def __init__(
        self,
        directive: Optional[str] = None,
        max_image_size: Optional[int] = 512,
        cache_max_size: int = 50,
        timeout: float = 120.0,
    ) -> None:
        super().__init__("vision_judge", directive)
        self.max_image_size = max_image_size
        self.cache_max_size = cache_max_size
        self.timeout = timeout
        self._cache: OrderedDict[str, JudgementResult] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _downsample_image(self, image: np.ndarray, max_size: int) -> np.ndarray:
        h, w = image.shape[:2]
        if h <= max_size and w <= max_size:
            return image
        scale = max_size / max(h, w)
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _compute_cache_key(
        self,
        original: np.ndarray,
        processed: np.ndarray,
        purpose: str,
        pipeline_name: str,
    ) -> str:
        h = hashlib.sha256()
        h.update(original.tobytes())
        h.update(processed.tobytes())
        h.update(purpose.encode())
        h.update(pipeline_name.encode())
        return h.hexdigest()

    def clear_cache(self) -> None:
        self._cache.clear()

    def get_cache_stats(self) -> dict:
        return {"hits": self._hits, "misses": self._misses}

    async def execute(
        self,
        original_image: np.ndarray,
        processed_image: np.ndarray,
        purpose: str,
        pipeline_name: str,
    ) -> JudgementResult:
        if self.max_image_size:
            orig = self._downsample_image(original_image, self.max_image_size)
            proc = self._downsample_image(processed_image, self.max_image_size)
        else:
            orig = original_image
            proc = processed_image

        cache_key = self._compute_cache_key(orig, proc, purpose, pipeline_name)
        if cache_key in self._cache:
            self._hits += 1
            return self._cache[cache_key]

        self._misses += 1

        prompt = build_vision_judge_prompt(
            purpose=purpose,
            pipeline_name=pipeline_name,
            directive=self.get_directive(),
        )
        images = [_encode_image(orig), _encode_image(proc)]

        for attempt in range(2):
            try:
                if self.timeout > 0:
                    response = await asyncio.wait_for(
                        ollama_client.generate_with_images(
                            prompt, images, system=VISION_JUDGE_SYSTEM_PROMPT
                        ),
                        timeout=self.timeout,
                    )
                else:
                    response = await ollama_client.generate_with_images(
                        prompt, images, system=VISION_JUDGE_SYSTEM_PROMPT
                    )
                if not response:
                    raise ValueError("Empty response from Ollama")
                result = _parse_response(response)
                self._log("INFO", f"Judgement complete for pipeline '{pipeline_name}'")
                if self.cache_max_size > 0:
                    if len(self._cache) >= self.cache_max_size:
                        self._cache.popitem(last=False)
                    self._cache[cache_key] = result
                return result
            except OllamaError:
                raise
            except asyncio.TimeoutError:
                raise
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                if attempt == 1:
                    self._log("ERROR", f"Failed to parse Ollama response after retry: {exc}")
                    raise ValueError(
                        f"VisionJudgeAgent: unparseable response after 2 attempts — {exc}"
                    ) from exc
