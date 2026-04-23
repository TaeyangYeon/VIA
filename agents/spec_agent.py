"""Spec agent for extracting mode, goals, and success criteria from user text."""

import json
import re
from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import InspectionMode, SpecResult
from agents.prompts.spec_prompt import SPEC_SYSTEM_PROMPT, build_spec_prompt
from backend.services.ollama_client import ollama_client

_INSPECTION_DEFAULTS = {"accuracy": 0.95, "fp_rate": 0.05, "fn_rate": 0.05}
_ALIGN_DEFAULTS = {"coord_error": 2.0, "success_rate": 0.9}


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _apply_defaults(mode: InspectionMode, criteria: dict) -> dict:
    if mode == InspectionMode.align:
        defaults = _ALIGN_DEFAULTS
    else:
        defaults = _INSPECTION_DEFAULTS
    return {**defaults, **criteria}


class SpecAgent(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("spec", directive)

    async def execute(self, user_text: str) -> SpecResult:
        prompt = build_spec_prompt(user_text, directive=self.get_directive())
        self._log("INFO", "Sending spec request", {"user_text": user_text})

        raw = await ollama_client.generate(prompt, system=SPEC_SYSTEM_PROMPT)
        self._log("INFO", "Received spec response", {"raw": raw[:200]})

        data = await self._parse_with_retry(raw, prompt)
        return self._build_result(data)

    async def _parse_with_retry(self, raw: str, original_prompt: str) -> dict:
        try:
            return _extract_json(raw)
        except (json.JSONDecodeError, ValueError):
            self._log("INFO", "JSON parse failed; retrying with fix prompt")
            fix_prompt = (
                f"{original_prompt}\n\n"
                "Your previous response was not valid JSON. "
                "Output ONLY the JSON object, nothing else."
            )
            raw2 = await ollama_client.generate(fix_prompt, system=SPEC_SYSTEM_PROMPT)
            try:
                return _extract_json(raw2)
            except (json.JSONDecodeError, ValueError) as exc:
                self._log("ERROR", "JSON parse failed after retry")
                raise ValueError(f"SpecAgent: could not parse JSON after retry: {raw2!r}") from exc

    def _build_result(self, data: dict) -> SpecResult:
        raw_mode = data.get("mode", "")
        try:
            mode = InspectionMode(raw_mode)
        except ValueError:
            self._log("WARNING", f"Unrecognized mode {raw_mode!r}; defaulting to inspection")
            mode = InspectionMode.inspection

        goal = data.get("goal", "")
        criteria = _apply_defaults(mode, data.get("success_criteria") or {})
        return SpecResult(mode=mode, goal=goal, success_criteria=criteria)
