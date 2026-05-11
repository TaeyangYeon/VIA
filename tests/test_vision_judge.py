"""Tests for Vision Judge Agent (Step 17) — ALL Ollama calls mocked."""
from __future__ import annotations

import base64
import inspect
import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from agents.models import JudgementResult
from agents.prompts.vision_judge_prompt import (
    VISION_JUDGE_SYSTEM_PROMPT,
    build_vision_judge_prompt,
)
from agents.vision_judge_agent import VisionJudgeAgent


# ── helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


def _make_gray(h: int = 64, w: int = 64) -> np.ndarray:
    return np.full((h, w), 128, dtype=np.uint8)


def _make_color(h: int = 64, w: int = 64) -> np.ndarray:
    return np.full((h, w, 3), (100, 150, 200), dtype=np.uint8)


def _good_json(**overrides) -> str:
    data = {
        "visibility_score": 0.8,
        "separability_score": 0.7,
        "measurability_score": 0.9,
        "problems": ["문제 없음"],
        "next_suggestion": "계속 진행하세요",
    }
    data.update(overrides)
    return json.dumps(data)


# ── Prompt module ─────────────────────────────────────────────────────────────

class TestVisionJudgeSystemPrompt:
    def test_constant_exists(self):
        assert isinstance(VISION_JUDGE_SYSTEM_PROMPT, str)
        assert len(VISION_JUDGE_SYSTEM_PROMPT) > 50

    def test_contains_judge_term(self):
        low = VISION_JUDGE_SYSTEM_PROMPT.lower()
        assert "judge" in low or "quality" in low or "vision" in low

    def test_contains_json_instruction(self):
        low = VISION_JUDGE_SYSTEM_PROMPT.lower()
        assert "json" in low

    def test_contains_score_terms(self):
        assert "visibility_score" in VISION_JUDGE_SYSTEM_PROMPT
        assert "separability_score" in VISION_JUDGE_SYSTEM_PROMPT
        assert "measurability_score" in VISION_JUDGE_SYSTEM_PROMPT

    def test_contains_problems_key(self):
        assert "problems" in VISION_JUDGE_SYSTEM_PROMPT

    def test_contains_next_suggestion_key(self):
        assert "next_suggestion" in VISION_JUDGE_SYSTEM_PROMPT


class TestBuildVisionJudgePrompt:
    def test_includes_purpose(self):
        prompt = build_vision_judge_prompt(purpose="crack detection", pipeline_name="edge_pipeline")
        assert "crack detection" in prompt

    def test_includes_pipeline_name(self):
        prompt = build_vision_judge_prompt(purpose="scratch", pipeline_name="blur_threshold")
        assert "blur_threshold" in prompt

    def test_no_directive_by_default(self):
        prompt = build_vision_judge_prompt(purpose="dust", pipeline_name="adaptive")
        assert "directive" not in prompt.lower()

    def test_directive_appended_when_provided(self):
        prompt = build_vision_judge_prompt(
            purpose="dust", pipeline_name="adaptive", directive="focus on edges"
        )
        assert "focus on edges" in prompt

    def test_directive_none_omitted(self):
        prompt_no = build_vision_judge_prompt(purpose="x", pipeline_name="y", directive=None)
        prompt_with = build_vision_judge_prompt(purpose="x", pipeline_name="y", directive="hint")
        assert len(prompt_with) > len(prompt_no)

    def test_json_format_instruction_present(self):
        prompt = build_vision_judge_prompt(purpose="blob", pipeline_name="morph")
        low = prompt.lower()
        assert "json" in low or "format" in low or "respond" in low


# ── Class structure ───────────────────────────────────────────────────────────

class TestVisionJudgeAgentStructure:
    def test_inherits_base_agent(self):
        from agents.base_agent import BaseAgent
        assert issubclass(VisionJudgeAgent, BaseAgent)

    def test_agent_name(self):
        agent = VisionJudgeAgent()
        assert agent.agent_name == "vision_judge"

    def test_execute_is_coroutine(self):
        agent = VisionJudgeAgent()
        assert inspect.iscoroutinefunction(agent.execute)

    def test_accepts_directive_in_constructor(self):
        agent = VisionJudgeAgent(directive="custom directive")
        assert agent.get_directive() == "custom directive"

    def test_set_directive_works(self):
        agent = VisionJudgeAgent()
        agent.set_directive("updated directive")
        assert agent.get_directive() == "updated directive"


# ── Execute happy path ────────────────────────────────────────────────────────

class TestVisionJudgeExecuteHappyPath:
    @pytest.fixture
    def agent(self):
        return VisionJudgeAgent()

    @pytest.mark.anyio
    async def test_returns_judgement_result(self, agent):
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=_good_json()),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="crack",
                pipeline_name="edge",
            )
        assert isinstance(result, JudgementResult)

    @pytest.mark.anyio
    async def test_scores_in_range(self, agent):
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=_good_json()),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="crack",
                pipeline_name="edge",
            )
        assert 0.0 <= result.visibility_score <= 1.0
        assert 0.0 <= result.separability_score <= 1.0
        assert 0.0 <= result.measurability_score <= 1.0

    @pytest.mark.anyio
    async def test_problems_is_list_of_str(self, agent):
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=_good_json()),
        ):
            result = await agent.execute(
                original_image=_make_color(),
                processed_image=_make_color(),
                purpose="dust",
                pipeline_name="blur",
            )
        assert isinstance(result.problems, list)
        assert all(isinstance(p, str) for p in result.problems)

    @pytest.mark.anyio
    async def test_next_suggestion_is_str(self, agent):
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=_good_json()),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="scratch",
                pipeline_name="morph",
            )
        assert isinstance(result.next_suggestion, str)

    @pytest.mark.anyio
    async def test_both_images_sent_to_generate_with_images(self, agent):
        mock_gen = AsyncMock(return_value=_good_json())
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_color(),
                purpose="blob",
                pipeline_name="threshold",
            )
        mock_gen.assert_called_once()
        _, kwargs = mock_gen.call_args
        images_arg = mock_gen.call_args[0][1] if len(mock_gen.call_args[0]) > 1 else kwargs.get("images", [])
        assert len(images_arg) == 2


# ── JSON parsing robustness ───────────────────────────────────────────────────

class TestJsonParsingRobustness:
    @pytest.fixture
    def agent(self):
        return VisionJudgeAgent()

    @pytest.mark.anyio
    async def test_handles_markdown_code_fence(self, agent):
        fenced = f"```json\n{_good_json()}\n```"
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=fenced),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert isinstance(result, JudgementResult)

    @pytest.mark.anyio
    async def test_handles_plain_json(self, agent):
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=_good_json()),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert isinstance(result, JudgementResult)

    @pytest.mark.anyio
    async def test_retries_once_on_invalid_json_then_succeeds(self, agent):
        mock_gen = AsyncMock(side_effect=["invalid json!!!", _good_json()])
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert isinstance(result, JudgementResult)
        assert mock_gen.call_count == 2

    @pytest.mark.anyio
    async def test_raises_value_error_after_two_failures(self, agent):
        mock_gen = AsyncMock(side_effect=["bad json", "also bad json"])
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            with pytest.raises(ValueError):
                await agent.execute(
                    original_image=_make_gray(),
                    processed_image=_make_gray(),
                    purpose="x",
                    pipeline_name="y",
                )


# ── Score clamping ────────────────────────────────────────────────────────────

class TestScoreClamping:
    @pytest.fixture
    def agent(self):
        return VisionJudgeAgent()

    @pytest.mark.anyio
    async def test_scores_above_one_clamped(self, agent):
        over = _good_json(visibility_score=1.5, separability_score=2.0, measurability_score=1.1)
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=over),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert result.visibility_score == 1.0
        assert result.separability_score == 1.0
        assert result.measurability_score == 1.0

    @pytest.mark.anyio
    async def test_scores_below_zero_clamped(self, agent):
        under = _good_json(visibility_score=-0.5, separability_score=-1.0, measurability_score=-0.1)
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=under),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert result.visibility_score == 0.0
        assert result.separability_score == 0.0
        assert result.measurability_score == 0.0

    @pytest.mark.anyio
    async def test_negative_scores_clamped_to_zero(self, agent):
        neg = _good_json(visibility_score=-99.0)
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(return_value=neg),
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert result.visibility_score == 0.0


# ── Image encoding ────────────────────────────────────────────────────────────

class TestImageEncoding:
    @pytest.fixture
    def agent(self):
        return VisionJudgeAgent()

    @pytest.mark.anyio
    async def test_grayscale_image_encoded_as_base64_png(self, agent):
        mock_gen = AsyncMock(return_value=_good_json())
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        images = mock_gen.call_args[0][1]
        for img_b64 in images:
            decoded = base64.b64decode(img_b64)
            assert decoded[:4] == b"\x89PNG"  # PNG magic bytes

    @pytest.mark.anyio
    async def test_color_image_encoded_correctly(self, agent):
        mock_gen = AsyncMock(return_value=_good_json())
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            await agent.execute(
                original_image=_make_color(),
                processed_image=_make_color(),
                purpose="x",
                pipeline_name="y",
            )
        images = mock_gen.call_args[0][1]
        for img_b64 in images:
            decoded = base64.b64decode(img_b64)
            assert decoded[:4] == b"\x89PNG"

    @pytest.mark.anyio
    async def test_no_data_uri_prefix_in_images(self, agent):
        mock_gen = AsyncMock(return_value=_good_json())
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_color(),
                purpose="x",
                pipeline_name="y",
            )
        images = mock_gen.call_args[0][1]
        for img_b64 in images:
            assert not img_b64.startswith("data:")


# ── Directive support ─────────────────────────────────────────────────────────

class TestDirectiveSupport:
    @pytest.mark.anyio
    async def test_directive_passed_to_prompt(self):
        agent = VisionJudgeAgent(directive="highlight bright regions")
        mock_gen = AsyncMock(return_value=_good_json())
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="dust",
                pipeline_name="median",
            )
        prompt_used = mock_gen.call_args[0][0]
        assert "highlight bright regions" in prompt_used

    @pytest.mark.anyio
    async def test_no_directive_prompt_without_directive_section(self):
        agent = VisionJudgeAgent()
        mock_gen = AsyncMock(return_value=_good_json())
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="dust",
                pipeline_name="median",
            )
        prompt_used = mock_gen.call_args[0][0]
        assert "directive" not in prompt_used.lower()


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.fixture
    def agent(self):
        return VisionJudgeAgent()

    @pytest.mark.anyio
    async def test_ollama_error_propagated(self, agent):
        from backend.services.ollama_client import OllamaError
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(side_effect=OllamaError("server error")),
        ):
            with pytest.raises(OllamaError):
                await agent.execute(
                    original_image=_make_gray(),
                    processed_image=_make_gray(),
                    purpose="x",
                    pipeline_name="y",
                )

    @pytest.mark.anyio
    async def test_ollama_connection_error_propagated(self, agent):
        from backend.services.ollama_client import OllamaConnectionError
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=AsyncMock(side_effect=OllamaConnectionError("unreachable")),
        ):
            with pytest.raises(OllamaConnectionError):
                await agent.execute(
                    original_image=_make_gray(),
                    processed_image=_make_gray(),
                    purpose="x",
                    pipeline_name="y",
                )

    @pytest.mark.anyio
    async def test_empty_response_triggers_retry(self, agent):
        mock_gen = AsyncMock(side_effect=["", _good_json()])
        with patch(
            "agents.vision_judge_agent.ollama_client.generate_with_images",
            new=mock_gen,
        ):
            result = await agent.execute(
                original_image=_make_gray(),
                processed_image=_make_gray(),
                purpose="x",
                pipeline_name="y",
            )
        assert isinstance(result, JudgementResult)
        assert mock_gen.call_count == 2
