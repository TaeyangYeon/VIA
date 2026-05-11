"""Prompt templates for Algorithm Coder Inspection Agent."""
from typing import Optional

from agents.models import AlgorithmCategory, InspectionItem

CODER_INSPECTION_SYSTEM_PROMPT = """\
You are an industrial OpenCV computer vision code generator.
Given an inspection item specification and a processing pipeline, generate a Python function that inspects an image.

Output ONLY a single valid JSON object — no explanation, no markdown, no code fences.

Output format:
{
  "code": "<complete Python function as a string>",
  "explanation": "<Korean explanation of what the function does>"
}

The generated function MUST follow this exact signature:
  def inspect_item(image: np.ndarray) -> dict

The function MUST return a dict with at minimum:
  {"result": "OK" or "NG", "details": {...}}

Rules:
- Use ONLY cv2 and numpy (import cv2, import numpy as np) — no other imports.
- The function must be standalone and complete.
- Incorporate the provided pipeline processing steps in the implementation.
- The explanation must be written in Korean.
- Output ONLY the JSON object. No prose, no code fences."""


def build_coder_inspection_prompt(
    item: InspectionItem,
    category: AlgorithmCategory,
    pipeline_summary: str,
    directive: Optional[str] = None,
) -> str:
    prompt = (
        f"Inspection item: {item.name}\n"
        f"Purpose: {item.purpose}\n"
        f"Method: {item.method.value if hasattr(item.method, 'value') else item.method}\n"
        f"Success criteria: {item.success_criteria}\n"
        f"Algorithm category: {category.value if hasattr(category, 'value') else category}\n"
        f"Pipeline steps: {pipeline_summary}"
    )
    if directive:
        prompt += f"\n\nAdditional directive: {directive}"
    return prompt
