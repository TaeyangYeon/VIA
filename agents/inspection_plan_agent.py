"""Inspection plan agent for designing multi-step inspection item lists."""
from __future__ import annotations

import json
import re
from typing import Optional

from agents.base_agent import BaseAgent
from agents.models import AlgorithmCategory, InspectionItem, InspectionPlan
from agents.prompts.inspection_plan_prompt import (
    INSPECTION_PLAN_SYSTEM_PROMPT,
    build_inspection_plan_prompt,
)
from backend.services.ollama_client import OllamaError, ollama_client


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


class InspectionPlanAgent(BaseAgent):
    def __init__(self, directive: Optional[str] = None) -> None:
        super().__init__("inspection_plan", directive)

    async def execute(self, purpose: str, image_diagnosis_summary: str) -> InspectionPlan:
        prompt = build_inspection_plan_prompt(
            purpose, image_diagnosis_summary, directive=self.get_directive()
        )
        raw = await ollama_client.generate(prompt, system=INSPECTION_PLAN_SYSTEM_PROMPT)
        return await self._parse_with_retry(raw, prompt)

    async def _parse_with_retry(self, raw: str, original_prompt: str) -> InspectionPlan:
        try:
            plan = self._build_plan(raw)
            self._log("INFO", f"Inspection plan created with {len(plan.items)} items")
            return plan
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            self._log("INFO", "Parse failed; retrying with fix prompt")
            fix_prompt = (
                f"{original_prompt}\n\n"
                "Your previous response was not valid JSON or contained no items. "
                "Output ONLY the JSON object, nothing else."
            )
            raw2 = await ollama_client.generate(fix_prompt, system=INSPECTION_PLAN_SYSTEM_PROMPT)
            try:
                plan = self._build_plan(raw2)
                self._log("INFO", f"Inspection plan created with {len(plan.items)} items")
                return plan
            except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
                self._log("ERROR", "Failed to parse inspection plan after retry")
                raise ValueError(
                    f"InspectionPlanAgent: could not parse plan after retry: {raw2!r}"
                ) from exc

    def _build_plan(self, raw: str) -> InspectionPlan:
        cleaned = _strip_fences(raw)
        data = json.loads(cleaned)
        raw_items = data.get("items", [])
        if not raw_items:
            raise ValueError("Empty items list in response")
        items = [self._build_item(d) for d in raw_items]
        items = self._validate_dependencies(items)
        return InspectionPlan(items=items)

    def _build_item(self, d: dict) -> InspectionItem:
        raw_method = d.get("method", "")
        try:
            method = AlgorithmCategory(raw_method)
        except ValueError:
            self._log("WARNING", f"Invalid method {raw_method!r}; defaulting to BLOB")
            method = AlgorithmCategory.BLOB
        return InspectionItem(
            id=int(d["id"]),
            name=str(d["name"]),
            purpose=str(d.get("purpose", "")),
            method=method,
            depends_on=[int(x) for x in d.get("depends_on", [])],
            safety_role=str(d.get("safety_role", "")),
            success_criteria=str(d.get("success_criteria", "")),
        )

    def _validate_dependencies(self, items: list[InspectionItem]) -> list[InspectionItem]:
        valid_ids: set[int] = set()
        for item in items:
            invalid = [dep for dep in item.depends_on if dep not in valid_ids]
            if invalid:
                self._log(
                    "WARNING",
                    f"Item {item.id}: removing invalid depends_on {invalid}",
                )
                item.depends_on = [d for d in item.depends_on if d in valid_ids]
            valid_ids.add(item.id)
        return items
