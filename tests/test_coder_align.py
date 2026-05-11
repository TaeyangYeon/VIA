"""Tests for Algorithm Coder Agent (Align mode) — Step 21."""
import inspect
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    PipelineBlock,
    ProcessingPipeline,
)
from agents.prompts.coder_align_prompt import (
    CODER_ALIGN_SYSTEM_PROMPT,
    build_coder_align_prompt,
)
from agents.algorithm_coder_align import AlgorithmCoderAlign
from agents.base_agent import BaseAgent
from backend.services.ollama_client import (
    OllamaError,
    OllamaConnectionError,
    OllamaGenerationError,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def simple_pipeline():
    return ProcessingPipeline(
        name="align_pipeline",
        blocks=[
            PipelineBlock(name="grayscale", when_condition="always", params=None),
            PipelineBlock(name="gaussian_blur", when_condition="always", params={"ksize": 5}),
        ],
        score=0.9,
    )


@pytest.fixture
def empty_pipeline():
    return ProcessingPipeline(name="empty", blocks=[], score=0.5)


@pytest.fixture
def single_block_pipeline():
    return ProcessingPipeline(
        name="single",
        blocks=[PipelineBlock(name="grayscale", when_condition="always", params=None)],
        score=1.0,
    )


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.generate = AsyncMock(return_value=json.dumps({
        "code": "def align(image):\n    pass",
        "explanation": "정렬 함수",
    }))
    return client


GOOD_JSON = json.dumps({"code": "def align(image):\n    pass", "explanation": "정렬 함수"})
FENCED_JSON = f"```json\n{GOOD_JSON}\n```"
PLAIN_FENCED_JSON = f"```\n{GOOD_JSON}\n```"


# ══════════════════════════════════════════════════════════════════════════════
# 1. System Prompt Content
# ══════════════════════════════════════════════════════════════════════════════

class TestCoderAlignSystemPrompt:
    def test_is_string(self):
        assert isinstance(CODER_ALIGN_SYSTEM_PROMPT, str)

    def test_not_empty(self):
        assert len(CODER_ALIGN_SYSTEM_PROMPT.strip()) > 50

    def test_enforces_align_signature(self):
        assert "align(image: np.ndarray) -> dict" in CODER_ALIGN_SYSTEM_PROMPT

    def test_enforces_return_x(self):
        assert '"x"' in CODER_ALIGN_SYSTEM_PROMPT

    def test_enforces_return_y(self):
        assert '"y"' in CODER_ALIGN_SYSTEM_PROMPT

    def test_enforces_return_confidence(self):
        assert '"confidence"' in CODER_ALIGN_SYSTEM_PROMPT

    def test_enforces_return_method_used(self):
        assert '"method_used"' in CODER_ALIGN_SYSTEM_PROMPT

    def test_includes_template_matching(self):
        assert "template_matching" in CODER_ALIGN_SYSTEM_PROMPT.lower()

    def test_includes_edge_detection(self):
        assert "edge_detection" in CODER_ALIGN_SYSTEM_PROMPT.lower()

    def test_includes_caliper(self):
        assert "caliper" in CODER_ALIGN_SYSTEM_PROMPT.lower()

    def test_fallback_order_template_before_edge(self):
        lower = CODER_ALIGN_SYSTEM_PROMPT.lower()
        assert lower.index("template_matching") < lower.index("edge_detection")

    def test_fallback_order_edge_before_caliper(self):
        lower = CODER_ALIGN_SYSTEM_PROMPT.lower()
        assert lower.index("edge_detection") < lower.index("caliper")

    def test_forbids_edge_learning(self):
        lower = CODER_ALIGN_SYSTEM_PROMPT.lower()
        assert "edge learning" in lower or "el " in lower or "forbid" in lower

    def test_forbids_deep_learning(self):
        lower = CODER_ALIGN_SYSTEM_PROMPT.lower()
        assert "deep learning" in lower or "dl " in lower or "forbid" in lower

    def test_requires_korean_explanation(self):
        assert "korean" in CODER_ALIGN_SYSTEM_PROMPT.lower() or "한국어" in CODER_ALIGN_SYSTEM_PROMPT

    def test_requires_cv2(self):
        assert "cv2" in CODER_ALIGN_SYSTEM_PROMPT

    def test_requires_numpy(self):
        assert "numpy" in CODER_ALIGN_SYSTEM_PROMPT.lower() or "np" in CODER_ALIGN_SYSTEM_PROMPT

    def test_json_output_only(self):
        assert "json" in CODER_ALIGN_SYSTEM_PROMPT.lower()

    def test_hw_improvement_for_failure(self):
        lower = CODER_ALIGN_SYSTEM_PROMPT.lower()
        assert "hardware" in lower or "hw" in lower or "lighting" in lower or "fixture" in lower


# ══════════════════════════════════════════════════════════════════════════════
# 2. Builder Function
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildCoderAlignPrompt:
    def test_returns_string(self):
        assert isinstance(build_coder_align_prompt("grayscale, gaussian_blur"), str)

    def test_includes_pipeline_summary(self):
        summary = "grayscale, gaussian_blur(ksize=5)"
        assert summary in build_coder_align_prompt(summary)

    def test_includes_directive_when_provided(self):
        assert "prefer_canny" in build_coder_align_prompt("grayscale", directive="prefer_canny")

    def test_no_directive_section_when_none(self):
        result = build_coder_align_prompt("grayscale", directive=None)
        assert "Additional directive" not in result

    def test_directive_default_is_none(self):
        sig = inspect.signature(build_coder_align_prompt)
        assert sig.parameters["directive"].default is None

    def test_handles_empty_pipeline_summary(self):
        result = build_coder_align_prompt("")
        assert isinstance(result, str) and len(result) > 0

    def test_not_empty(self):
        assert len(build_coder_align_prompt("step1").strip()) > 10


# ══════════════════════════════════════════════════════════════════════════════
# 3. Class Structure
# ══════════════════════════════════════════════════════════════════════════════

class TestAlgorithmCoderAlignStructure:
    def test_inherits_base_agent(self):
        assert issubclass(AlgorithmCoderAlign, BaseAgent)

    def test_agent_name(self):
        agent = AlgorithmCoderAlign(ollama_client=MagicMock())
        assert agent.agent_name == "algorithm_coder_align"

    def test_execute_is_coroutine(self):
        assert inspect.iscoroutinefunction(AlgorithmCoderAlign.execute)

    def test_accepts_ollama_client_param(self):
        mock = MagicMock()
        assert AlgorithmCoderAlign(ollama_client=mock)._ollama is mock

    def test_accepts_directive_param(self):
        agent = AlgorithmCoderAlign(ollama_client=MagicMock(), directive="test_directive")
        assert agent.get_directive() == "test_directive"

    def test_default_directive_is_none(self):
        agent = AlgorithmCoderAlign(ollama_client=MagicMock())
        assert agent.get_directive() is None


# ══════════════════════════════════════════════════════════════════════════════
# 4. Execute Core
# ══════════════════════════════════════════════════════════════════════════════

class TestAlgorithmCoderAlignExecute:
    @pytest.mark.anyio
    async def test_returns_algorithm_result(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        assert isinstance(await agent.execute(pipeline=simple_pipeline), AlgorithmResult)

    @pytest.mark.anyio
    async def test_category_is_template_matching(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        result = await agent.execute(pipeline=simple_pipeline)
        assert result.category == AlgorithmCategory.TEMPLATE_MATCHING

    @pytest.mark.anyio
    async def test_code_from_llm(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        result = await agent.execute(pipeline=simple_pipeline)
        assert result.code == "def align(image):\n    pass"

    @pytest.mark.anyio
    async def test_explanation_from_llm(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        result = await agent.execute(pipeline=simple_pipeline)
        assert result.explanation == "정렬 함수"

    @pytest.mark.anyio
    async def test_pipeline_preserved(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        result = await agent.execute(pipeline=simple_pipeline)
        assert result.pipeline is simple_pipeline

    @pytest.mark.anyio
    async def test_calls_ollama_once(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        await agent.execute(pipeline=simple_pipeline)
        assert mock_ollama.generate.call_count == 1

    @pytest.mark.anyio
    async def test_uses_system_prompt(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        await agent.execute(pipeline=simple_pipeline)
        call_kwargs = mock_ollama.generate.call_args
        system_arg = call_kwargs.kwargs.get("system") or (
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
        )
        assert system_arg == CODER_ALIGN_SYSTEM_PROMPT

    @pytest.mark.anyio
    async def test_pipeline_summary_in_prompt(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        await agent.execute(pipeline=simple_pipeline)
        prompt_arg = mock_ollama.generate.call_args[0][0]
        assert "grayscale" in prompt_arg


# ══════════════════════════════════════════════════════════════════════════════
# 5. JSON Parsing Robustness
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonParsing:
    @pytest.mark.anyio
    async def test_parses_clean_json(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(return_value=GOOD_JSON)
        result = await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)
        assert result.code == "def align(image):\n    pass"

    @pytest.mark.anyio
    async def test_strips_json_code_fence(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(return_value=FENCED_JSON)
        result = await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)
        assert result.code == "def align(image):\n    pass"

    @pytest.mark.anyio
    async def test_strips_plain_code_fence(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(return_value=PLAIN_FENCED_JSON)
        result = await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)
        assert result.code == "def align(image):\n    pass"

    @pytest.mark.anyio
    async def test_retries_on_first_parse_failure(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=["not valid json !!!", GOOD_JSON])
        result = await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)
        assert result.code == "def align(image):\n    pass"
        assert client.generate.call_count == 2

    @pytest.mark.anyio
    async def test_retries_on_empty_response(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=["", GOOD_JSON])
        result = await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)
        assert result.code == "def align(image):\n    pass"
        assert client.generate.call_count == 2

    @pytest.mark.anyio
    async def test_raises_value_error_on_two_parse_failures(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=["invalid json", "still invalid json"])
        with pytest.raises(ValueError):
            await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)

    @pytest.mark.anyio
    async def test_raises_value_error_on_two_empty_responses(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=["", ""])
        with pytest.raises(ValueError):
            await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Error Handling
# ══════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    @pytest.mark.anyio
    async def test_ollama_error_propagates(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=OllamaError("base error"))
        with pytest.raises(OllamaError):
            await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)

    @pytest.mark.anyio
    async def test_ollama_connection_error_propagates(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=OllamaConnectionError("connection failed"))
        with pytest.raises(OllamaConnectionError):
            await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)

    @pytest.mark.anyio
    async def test_ollama_generation_error_propagates(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=OllamaGenerationError("generation failed"))
        with pytest.raises(OllamaGenerationError):
            await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)

    @pytest.mark.anyio
    async def test_ollama_error_not_caught_on_retry(self, simple_pipeline):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=["invalid json", OllamaError("second attempt failed")])
        with pytest.raises(OllamaError):
            await AlgorithmCoderAlign(ollama_client=client).execute(pipeline=simple_pipeline)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Directive Support
# ══════════════════════════════════════════════════════════════════════════════

class TestDirective:
    def test_set_directive_updates_value(self):
        agent = AlgorithmCoderAlign(ollama_client=MagicMock())
        agent.set_directive("new_directive")
        assert agent.get_directive() == "new_directive"

    @pytest.mark.anyio
    async def test_directive_included_in_prompt(self, simple_pipeline):
        captured = []
        async def capture_generate(prompt, system=None):
            captured.append(prompt)
            return GOOD_JSON
        client = MagicMock()
        client.generate = capture_generate
        agent = AlgorithmCoderAlign(ollama_client=client, directive="use_orb_features")
        await agent.execute(pipeline=simple_pipeline)
        assert any("use_orb_features" in p for p in captured)

    @pytest.mark.anyio
    async def test_no_directive_not_in_prompt(self, simple_pipeline):
        captured = []
        async def capture_generate(prompt, system=None):
            captured.append(prompt)
            return GOOD_JSON
        client = MagicMock()
        client.generate = capture_generate
        agent = AlgorithmCoderAlign(ollama_client=client)
        await agent.execute(pipeline=simple_pipeline)
        for p in captured:
            assert "Additional directive" not in p


# ══════════════════════════════════════════════════════════════════════════════
# 8. Edge Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    @pytest.mark.anyio
    async def test_empty_pipeline_uses_no_preprocessing(self, mock_ollama, empty_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        await agent.execute(pipeline=empty_pipeline)
        assert "(no preprocessing)" in mock_ollama.generate.call_args[0][0]

    @pytest.mark.anyio
    async def test_pipeline_blocks_with_params_in_summary(self, mock_ollama, simple_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        await agent.execute(pipeline=simple_pipeline)
        assert "gaussian_blur" in mock_ollama.generate.call_args[0][0]

    @pytest.mark.anyio
    async def test_result_category_always_template_matching(self, mock_ollama, empty_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        result = await agent.execute(pipeline=empty_pipeline)
        assert result.category == AlgorithmCategory.TEMPLATE_MATCHING

    @pytest.mark.anyio
    async def test_result_pipeline_matches_input(self, mock_ollama, empty_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        result = await agent.execute(pipeline=empty_pipeline)
        assert result.pipeline is empty_pipeline

    @pytest.mark.anyio
    async def test_block_without_params_name_only_in_summary(self, mock_ollama, single_block_pipeline):
        agent = AlgorithmCoderAlign(ollama_client=mock_ollama)
        await agent.execute(pipeline=single_block_pipeline)
        prompt_arg = mock_ollama.generate.call_args[0][0]
        assert "grayscale" in prompt_arg
