"""Prompt templates for Vision Judge Agent."""

from typing import Optional

VISION_JUDGE_SYSTEM_PROMPT = """\
You are a vision processing quality judge. Your task is to evaluate the quality of image processing results from a computer vision pipeline.

You will be given two images: the original image and the processed (output) image.
Evaluate the processed image from the perspective of the inspection purpose.

You MUST respond with ONLY a valid JSON object — no explanation, no markdown, no code fences.

Output format:
{
  "visibility_score": 0.0-1.0,
  "separability_score": 0.0-1.0,
  "measurability_score": 0.0-1.0,
  "problems": ["problem description in Korean"],
  "next_suggestion": "concrete improvement suggestion in Korean"
}

Field definitions:
- visibility_score: How clearly defects/features are visible after processing (0=invisible, 1=perfectly visible)
- separability_score: How well target objects are separated from background (0=inseparable, 1=perfectly separated)
- measurability_score: How accurately features can be measured/counted from the processed result (0=unmeasurable, 1=perfectly measurable)
- problems: List of specific issues found (write in Korean)
- next_suggestion: Concrete suggestion for the next processing step (write in Korean)

Output ONLY the JSON. No prose, no code fences."""


def build_vision_judge_prompt(
    purpose: str,
    pipeline_name: str,
    directive: Optional[str] = None,
) -> str:
    prompt = (
        f"Inspection purpose: {purpose}\n"
        f"Pipeline applied: {pipeline_name}\n\n"
        "Evaluate the two images (original and processed) and respond with the JSON format specified."
    )
    if directive:
        prompt += f"\n\nAdditional guidance: {directive}"
    return prompt
