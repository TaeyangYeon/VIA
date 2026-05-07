"""Performance optimization tests for VisionJudgeAgent (Step 47).

Tests: image downsampling, result caching, timeout configuration, cache statistics.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from agents.models import JudgementResult
from agents.vision_judge_agent import VisionJudgeAgent


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


def _good_json(**overrides) -> str:
    data = {
        "visibility_score": 0.8,
        "separability_score": 0.7,
        "measurability_score": 0.9,
        "problems": [],
        "next_suggestion": "OK",
    }
    data.update(overrides)
    return json.dumps(data)


def _make_gray(h: int = 64, w: int = 64) -> np.ndarray:
    return np.full((h, w), 128, dtype=np.uint8)


def _make_color(h: int = 64, w: int = 64) -> np.ndarray:
    return np.full((h, w, 3), (100, 150, 200), dtype=np.uint8)


# ── constructor parameters ────────────────────────────────────────────────────

class TestConstructorParameters:
    def test_default_max_image_size_is_512(self):
        agent = VisionJudgeAgent()
        assert agent.max_image_size == 512

    def test_custom_max_image_size(self):
        agent = VisionJudgeAgent(max_image_size=256)
        assert agent.max_image_size == 256

    def test_zero_max_image_size_stored(self):
        agent = VisionJudgeAgent(max_image_size=0)
        assert agent.max_image_size == 0

    def test_none_max_image_size_stored(self):
        agent = VisionJudgeAgent(max_image_size=None)
        assert agent.max_image_size is None

    def test_default_cache_max_size_is_50(self):
        agent = VisionJudgeAgent()
        assert agent.cache_max_size == 50

    def test_custom_cache_max_size(self):
        agent = VisionJudgeAgent(cache_max_size=10)
        assert agent.cache_max_size == 10

    def test_default_timeout_is_120(self):
        agent = VisionJudgeAgent()
        assert agent.timeout == 120.0

    def test_custom_timeout(self):
        agent = VisionJudgeAgent(timeout=600.0)
        assert agent.timeout == 600.0

    def test_timeout_zero_stored(self):
        agent = VisionJudgeAgent(timeout=0.0)
        assert agent.timeout == 0.0

    def test_directive_still_works_with_new_params(self):
        agent = VisionJudgeAgent(directive="hint", max_image_size=256, timeout=300.0)
        assert agent.get_directive() == "hint"
        assert agent.max_image_size == 256
        assert agent.timeout == 300.0

    def test_clear_cache_method_exists(self):
        agent = VisionJudgeAgent()
        assert callable(agent.clear_cache)

    def test_get_cache_stats_method_exists(self):
        agent = VisionJudgeAgent()
        assert callable(agent.get_cache_stats)


# ── image downsampling ────────────────────────────────────────────────────────

class TestImageDownsampling:
    def test_landscape_downsampled_to_max_width(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=400, w=800)
        result = agent._downsample_image(img, 512)
        assert result.shape[1] == 512
        assert result.shape[0] == 256

    def test_portrait_downsampled_to_max_height(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=800, w=400)
        result = agent._downsample_image(img, 512)
        assert result.shape[0] == 512
        assert result.shape[1] == 256

    def test_small_image_not_changed(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=100, w=100)
        result = agent._downsample_image(img, 512)
        assert result.shape[:2] == (100, 100)

    def test_exact_max_size_not_changed(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=512, w=512)
        result = agent._downsample_image(img, 512)
        assert result.shape[:2] == (512, 512)

    def test_one_dim_equals_max_size_not_changed(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=512, w=400)
        result = agent._downsample_image(img, 512)
        assert result.shape[:2] == (512, 400)

    def test_aspect_ratio_preserved_landscape(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=300, w=900)
        result = agent._downsample_image(img, 512)
        h, w = result.shape[:2]
        assert w == 512
        assert abs(h / w - 300 / 900) < 0.02

    def test_aspect_ratio_preserved_portrait(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=900, w=300)
        result = agent._downsample_image(img, 512)
        h, w = result.shape[:2]
        assert h == 512
        assert abs(w / h - 300 / 900) < 0.02

    def test_grayscale_stays_grayscale(self):
        agent = VisionJudgeAgent()
        img = _make_gray(h=600, w=800)
        result = agent._downsample_image(img, 512)
        assert result.ndim == 2

    def test_color_stays_color(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=600, w=800)
        result = agent._downsample_image(img, 512)
        assert result.ndim == 3

    def test_returns_ndarray(self):
        agent = VisionJudgeAgent()
        img = _make_color(h=600, w=800)
        result = agent._downsample_image(img, 512)
        assert isinstance(result, np.ndarray)


class TestDownsamplingIntegration:
    @pytest.mark.anyio
    async def test_execute_with_large_image_returns_result(self):
        agent = VisionJudgeAgent(max_image_size=64)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            result = await agent.execute(
                original_image=_make_color(h=640, w=480),
                processed_image=_make_color(h=640, w=480),
                purpose="crack",
                pipeline_name="edge",
            )
        assert isinstance(result, JudgementResult)

    @pytest.mark.anyio
    async def test_execute_skips_downsampling_when_max_size_zero(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            result = await agent.execute(
                original_image=_make_color(h=640, w=480),
                processed_image=_make_color(h=640, w=480),
                purpose="crack",
                pipeline_name="edge",
            )
        assert isinstance(result, JudgementResult)
        mock_gen.assert_called_once()

    @pytest.mark.anyio
    async def test_execute_skips_downsampling_when_max_size_none(self):
        agent = VisionJudgeAgent(max_image_size=None)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            result = await agent.execute(
                original_image=_make_color(h=640, w=480),
                processed_image=_make_color(h=640, w=480),
                purpose="crack",
                pipeline_name="edge",
            )
        assert isinstance(result, JudgementResult)


# ── cache key ─────────────────────────────────────────────────────────────────

class TestCacheKey:
    def test_same_inputs_produce_same_key(self):
        agent = VisionJudgeAgent()
        img = _make_gray()
        k1 = agent._compute_cache_key(img, img, "purpose", "pipeline")
        k2 = agent._compute_cache_key(img, img, "purpose", "pipeline")
        assert k1 == k2

    def test_different_purpose_different_key(self):
        agent = VisionJudgeAgent()
        img = _make_gray()
        k1 = agent._compute_cache_key(img, img, "crack", "edge")
        k2 = agent._compute_cache_key(img, img, "dust", "edge")
        assert k1 != k2

    def test_different_pipeline_different_key(self):
        agent = VisionJudgeAgent()
        img = _make_gray()
        k1 = agent._compute_cache_key(img, img, "x", "pipeline_a")
        k2 = agent._compute_cache_key(img, img, "x", "pipeline_b")
        assert k1 != k2

    def test_different_original_image_different_key(self):
        agent = VisionJudgeAgent()
        img1 = _make_gray()
        img2 = img1.copy()
        img2[0, 0] = 255
        k1 = agent._compute_cache_key(img1, img1, "x", "y")
        k2 = agent._compute_cache_key(img2, img2, "x", "y")
        assert k1 != k2

    def test_key_is_str(self):
        agent = VisionJudgeAgent()
        img = _make_gray()
        key = agent._compute_cache_key(img, img, "x", "y")
        assert isinstance(key, str)

    def test_key_is_sha256_hex(self):
        agent = VisionJudgeAgent()
        img = _make_gray()
        key = agent._compute_cache_key(img, img, "x", "y")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# ── caching behavior ──────────────────────────────────────────────────────────

class TestCaching:
    @pytest.mark.anyio
    async def test_cache_miss_calls_ollama(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(_make_gray(), _make_gray(), purpose="x", pipeline_name="y")
        mock_gen.assert_called_once()

    @pytest.mark.anyio
    async def test_cache_hit_skips_ollama(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        img = _make_gray()
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(img, img, purpose="x", pipeline_name="y")
            await agent.execute(img, img, purpose="x", pipeline_name="y")
        assert mock_gen.call_count == 1

    @pytest.mark.anyio
    async def test_different_purpose_is_cache_miss(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        img = _make_gray()
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(img, img, purpose="crack", pipeline_name="edge")
            await agent.execute(img, img, purpose="dust", pipeline_name="edge")
        assert mock_gen.call_count == 2

    @pytest.mark.anyio
    async def test_different_pipeline_is_cache_miss(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        img = _make_gray()
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(img, img, purpose="crack", pipeline_name="edge")
            await agent.execute(img, img, purpose="crack", pipeline_name="morph")
        assert mock_gen.call_count == 2

    @pytest.mark.anyio
    async def test_different_image_is_cache_miss(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        img1 = _make_gray()
        img2 = img1.copy()
        img2[0, 0] = 255
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(img1, img1, purpose="x", pipeline_name="y")
            await agent.execute(img2, img2, purpose="x", pipeline_name="y")
        assert mock_gen.call_count == 2

    @pytest.mark.anyio
    async def test_clear_cache_forces_re_call(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        img = _make_gray()
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(img, img, purpose="x", pipeline_name="y")
            agent.clear_cache()
            await agent.execute(img, img, purpose="x", pipeline_name="y")
        assert mock_gen.call_count == 2

    @pytest.mark.anyio
    async def test_cache_returns_same_result_on_hit(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json(visibility_score=0.42))
        img = _make_gray()
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            r1 = await agent.execute(img, img, purpose="x", pipeline_name="y")
            r2 = await agent.execute(img, img, purpose="x", pipeline_name="y")
        assert r1.visibility_score == r2.visibility_score == 0.42

    @pytest.mark.anyio
    async def test_max_size_evicts_oldest_entry(self):
        agent = VisionJudgeAgent(max_image_size=0, cache_max_size=2)
        mock_gen = AsyncMock(return_value=_good_json())

        def unique_img(v: int) -> np.ndarray:
            img = _make_gray()
            img[0, 0] = v
            return img

        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            img0, img1, img2 = unique_img(0), unique_img(1), unique_img(2)
            await agent.execute(img0, img0, purpose="x", pipeline_name="y")  # miss 1
            await agent.execute(img1, img1, purpose="x", pipeline_name="y")  # miss 2
            await agent.execute(img2, img2, purpose="x", pipeline_name="y")  # miss 3, evicts img0
            await agent.execute(img0, img0, purpose="x", pipeline_name="y")  # miss 4, img0 gone
        assert mock_gen.call_count == 4


# ── cache statistics ──────────────────────────────────────────────────────────

class TestCacheStatistics:
    def test_initial_stats_are_zero(self):
        agent = VisionJudgeAgent()
        stats = agent.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_get_cache_stats_returns_dict(self):
        agent = VisionJudgeAgent()
        assert isinstance(agent.get_cache_stats(), dict)

    @pytest.mark.anyio
    async def test_miss_increments_misses(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(_make_gray(), _make_gray(), purpose="x", pipeline_name="y")
        stats = agent.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

    @pytest.mark.anyio
    async def test_hit_increments_hits(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        img = _make_gray()
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            await agent.execute(img, img, purpose="x", pipeline_name="y")
            await agent.execute(img, img, purpose="x", pipeline_name="y")
        stats = agent.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1

    def test_clear_cache_does_not_reset_stats(self):
        agent = VisionJudgeAgent()
        agent.clear_cache()
        stats = agent.get_cache_stats()
        assert "hits" in stats
        assert "misses" in stats

    @pytest.mark.anyio
    async def test_stats_accumulate_across_calls(self):
        agent = VisionJudgeAgent(max_image_size=0)
        mock_gen = AsyncMock(return_value=_good_json())
        base = _make_gray()

        def unique(v: int) -> np.ndarray:
            img = base.copy()
            img[0, 0] = v
            return img

        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            a, b = unique(1), unique(2)
            await agent.execute(a, a, purpose="x", pipeline_name="y")  # miss
            await agent.execute(b, b, purpose="x", pipeline_name="y")  # miss
            await agent.execute(a, a, purpose="x", pipeline_name="y")  # hit
            await agent.execute(b, b, purpose="x", pipeline_name="y")  # hit
        stats = agent.get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 2


# ── timeout ───────────────────────────────────────────────────────────────────

class TestTimeout:
    @pytest.mark.anyio
    async def test_timeout_triggers_on_slow_response(self):
        agent = VisionJudgeAgent(max_image_size=0, timeout=0.001)

        async def slow(*args, **kwargs):
            await asyncio.sleep(5.0)
            return _good_json()

        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=slow):
            with pytest.raises(asyncio.TimeoutError):
                await agent.execute(_make_gray(), _make_gray(), purpose="x", pipeline_name="y")

    @pytest.mark.anyio
    async def test_no_timeout_when_zero(self):
        agent = VisionJudgeAgent(max_image_size=0, timeout=0.0)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            result = await agent.execute(_make_gray(), _make_gray(), purpose="x", pipeline_name="y")
        assert isinstance(result, JudgementResult)

    @pytest.mark.anyio
    async def test_fast_response_does_not_timeout(self):
        agent = VisionJudgeAgent(max_image_size=0, timeout=10.0)
        mock_gen = AsyncMock(return_value=_good_json())
        with patch("agents.vision_judge_agent.ollama_client.generate_with_images", new=mock_gen):
            result = await agent.execute(_make_gray(), _make_gray(), purpose="x", pipeline_name="y")
        assert isinstance(result, JudgementResult)
