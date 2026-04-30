"""Tests for Algorithm Coder Inspection agent and prompt module."""
import inspect
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from agents.models import (
    AlgorithmCategory,
    AlgorithmResult,
    InspectionItem,
    InspectionPlan,
    InspectionMode,
    PipelineBlock,
    ProcessingPipeline,
)
from agents.prompts.coder_inspection_prompt import (
    CODER_INSPECTION_SYSTEM_PROMPT,
    build_coder_inspection_prompt,
)
from agents.algorithm_coder_inspection import AlgorithmCoderInspection
from agents.base_agent import BaseAgent
from backend.services.ollama_client import (
    OllamaError,
    OllamaConnectionError,
    OllamaGenerationError,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture
def sample_item():
    return InspectionItem(
        id=1,
        name="스크래치 검출",
        purpose="표면 스크래치 탐지",
        method=AlgorithmCategory.EDGE_DETECTION,
        depends_on=[],
        safety_role="주 검사",
        success_criteria="99% 이상 검출률",
    )


@pytest.fixture
def sample_pipeline():
    return ProcessingPipeline(
        name="edge_pipeline",
        blocks=[
            PipelineBlock(name="GaussianBlur", when_condition="always", params={"ksize": 5}),
            PipelineBlock(name="Canny", when_condition="always", params={"threshold1": 50}),
        ],
        score=0.85,
    )


@pytest.fixture
def sample_plan(sample_item):
    return InspectionPlan(items=[sample_item], mode=InspectionMode.inspection)


@pytest.fixture
def multi_item_plan():
    items = [
        InspectionItem(
            id=i,
            name=f"검사항목{i}",
            purpose=f"목적{i}",
            method=AlgorithmCategory.BLOB,
            success_criteria=f"기준{i}",
        )
        for i in range(1, 6)
    ]
    return InspectionPlan(items=items, mode=InspectionMode.inspection)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.generate = AsyncMock(return_value=json.dumps({
        "code": "def inspect_item(image):\n    return {'result': 'OK', 'details': {}}",
        "explanation": "이 함수는 이미지를 검사합니다.",
    }))
    return client


# ── 1. Prompt Module Tests ─────────────────────────────────────────────────

class TestCoderInspectionSystemPrompt:
    def test_system_prompt_exists(self):
        assert CODER_INSPECTION_SYSTEM_PROMPT is not None

    def test_system_prompt_non_empty(self):
        assert len(CODER_INSPECTION_SYSTEM_PROMPT.strip()) > 0

    def test_system_prompt_contains_opencv(self):
        assert "OpenCV" in CODER_INSPECTION_SYSTEM_PROMPT or "cv2" in CODER_INSPECTION_SYSTEM_PROMPT

    def test_system_prompt_contains_inspect(self):
        assert "inspect" in CODER_INSPECTION_SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_code(self):
        assert "code" in CODER_INSPECTION_SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_json(self):
        assert "JSON" in CODER_INSPECTION_SYSTEM_PROMPT or "json" in CODER_INSPECTION_SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_function(self):
        assert "inspect_item" in CODER_INSPECTION_SYSTEM_PROMPT

    def test_system_prompt_mentions_result_ok_ng(self):
        assert "OK" in CODER_INSPECTION_SYSTEM_PROMPT and "NG" in CODER_INSPECTION_SYSTEM_PROMPT

    def test_system_prompt_mentions_explanation(self):
        assert "explanation" in CODER_INSPECTION_SYSTEM_PROMPT.lower()

    def test_system_prompt_is_string(self):
        assert isinstance(CODER_INSPECTION_SYSTEM_PROMPT, str)


class TestBuildCoderInspectionPrompt:
    def test_includes_item_name(self, sample_item):
        prompt = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "summary")
        assert sample_item.name in prompt

    def test_includes_item_purpose(self, sample_item):
        prompt = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "summary")
        assert sample_item.purpose in prompt

    def test_includes_item_method(self, sample_item):
        prompt = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "summary")
        assert "EDGE_DETECTION" in prompt

    def test_includes_success_criteria(self, sample_item):
        prompt = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "summary")
        assert sample_item.success_criteria in prompt

    def test_includes_category(self, sample_item):
        prompt = build_coder_inspection_prompt(sample_item, AlgorithmCategory.BLOB, "summary")
        assert "BLOB" in prompt

    def test_includes_pipeline_summary(self, sample_item):
        prompt = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "GaussianBlur -> Canny")
        assert "GaussianBlur" in prompt

    def test_directive_included_when_provided(self, sample_item):
        prompt = build_coder_inspection_prompt(
            sample_item, AlgorithmCategory.EDGE_DETECTION, "summary", directive="use morphological ops"
        )
        assert "use morphological ops" in prompt

    def test_directive_excluded_when_none(self, sample_item):
        prompt = build_coder_inspection_prompt(
            sample_item, AlgorithmCategory.EDGE_DETECTION, "summary", directive=None
        )
        assert "directive" not in prompt.lower() or "Additional" not in prompt

    def test_returns_string(self, sample_item):
        result = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "summary")
        assert isinstance(result, str)

    def test_non_empty_prompt(self, sample_item):
        result = build_coder_inspection_prompt(sample_item, AlgorithmCategory.EDGE_DETECTION, "summary")
        assert len(result.strip()) > 0


# ── 2. Class Structure Tests ──────────────────────────────────────────────

class TestAlgorithmCoderInspectionStructure:
    def test_inherits_base_agent(self):
        assert issubclass(AlgorithmCoderInspection, BaseAgent)

    def test_agent_name(self, mock_client):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        assert agent.agent_name == "algorithm_coder_inspection"

    def test_execute_is_coroutine(self, mock_client):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        assert inspect.iscoroutinefunction(agent.execute)

    def test_directive_in_constructor(self, mock_client):
        agent = AlgorithmCoderInspection(ollama_client=mock_client, directive="test directive")
        assert agent.get_directive() == "test directive"

    def test_set_directive(self, mock_client):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        agent.set_directive("new directive")
        assert agent.get_directive() == "new directive"


# ── 3. Execute Core Tests ─────────────────────────────────────────────────

class TestAlgorithmCoderInspectionExecute:
    @pytest.mark.anyio
    async def test_returns_algorithm_result(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result, AlgorithmResult)

    @pytest.mark.anyio
    async def test_correct_category_set(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert result.category == AlgorithmCategory.EDGE_DETECTION

    @pytest.mark.anyio
    async def test_pipeline_stored_in_result(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert result.pipeline == sample_pipeline

    @pytest.mark.anyio
    async def test_generate_called_for_each_item(self, mock_client, sample_pipeline, multi_item_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        await agent.execute(
            category=AlgorithmCategory.BLOB,
            pipeline=sample_pipeline,
            plan=multi_item_plan,
        )
        assert mock_client.generate.call_count == 5

    @pytest.mark.anyio
    async def test_code_is_string(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result.code, str)

    @pytest.mark.anyio
    async def test_explanation_is_string(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result.explanation, str)

    @pytest.mark.anyio
    async def test_explanation_contains_korean(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert any("가" <= ch <= "힣" for ch in result.explanation)

    @pytest.mark.anyio
    async def test_system_prompt_passed_to_generate(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        call_kwargs = mock_client.generate.call_args
        assert call_kwargs is not None
        system_arg = call_kwargs.kwargs.get("system") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
        assert system_arg == CODER_INSPECTION_SYSTEM_PROMPT

    @pytest.mark.anyio
    async def test_pipeline_summary_includes_block_names(self, mock_client, sample_pipeline, sample_plan):
        captured_prompts = []
        async def capture_generate(prompt, system=None):
            captured_prompts.append(prompt)
            return json.dumps({
                "code": "def inspect_item(image): return {'result': 'OK', 'details': {}}",
                "explanation": "검사 함수입니다.",
            })
        mock_client.generate = capture_generate
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert any("GaussianBlur" in p for p in captured_prompts)
        assert any("Canny" in p for p in captured_prompts)


# ── 4. JSON Parsing Robustness ────────────────────────────────────────────

class TestJsonParsing:
    @pytest.mark.anyio
    async def test_handles_markdown_code_fence(self, sample_pipeline, sample_plan):
        client = MagicMock()
        client.generate = AsyncMock(return_value=(
            "```json\n"
            + json.dumps({"code": "def inspect_item(image): return {'result': 'OK', 'details': {}}", "explanation": "설명입니다."})
            + "\n```"
        ))
        agent = AlgorithmCoderInspection(ollama_client=client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result, AlgorithmResult)

    @pytest.mark.anyio
    async def test_handles_plain_json(self, sample_pipeline, sample_plan):
        client = MagicMock()
        client.generate = AsyncMock(return_value=json.dumps({
            "code": "def inspect_item(image): return {'result': 'OK', 'details': {}}",
            "explanation": "설명입니다.",
        }))
        agent = AlgorithmCoderInspection(ollama_client=client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert result.code != ""

    @pytest.mark.anyio
    async def test_retry_on_first_json_failure(self, sample_pipeline, sample_plan):
        client = MagicMock()
        good_response = json.dumps({
            "code": "def inspect_item(image): return {'result': 'OK', 'details': {}}",
            "explanation": "재시도 성공입니다.",
        })
        client.generate = AsyncMock(side_effect=["invalid json{{", good_response])
        agent = AlgorithmCoderInspection(ollama_client=client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result, AlgorithmResult)
        assert client.generate.call_count == 2

    @pytest.mark.anyio
    async def test_raises_value_error_on_double_json_failure(self, sample_pipeline, sample_plan):
        client = MagicMock()
        client.generate = AsyncMock(return_value="not valid json at all {{")
        agent = AlgorithmCoderInspection(ollama_client=client)
        with pytest.raises(ValueError):
            await agent.execute(
                category=AlgorithmCategory.EDGE_DETECTION,
                pipeline=sample_pipeline,
                plan=sample_plan,
            )


# ── 5. Error Handling ─────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.mark.anyio
    async def test_ollama_error_propagates(self, sample_pipeline, sample_plan):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=OllamaError("generic error"))
        agent = AlgorithmCoderInspection(ollama_client=client)
        with pytest.raises(OllamaError):
            await agent.execute(
                category=AlgorithmCategory.EDGE_DETECTION,
                pipeline=sample_pipeline,
                plan=sample_plan,
            )

    @pytest.mark.anyio
    async def test_ollama_connection_error_propagates(self, sample_pipeline, sample_plan):
        client = MagicMock()
        client.generate = AsyncMock(side_effect=OllamaConnectionError("no connection"))
        agent = AlgorithmCoderInspection(ollama_client=client)
        with pytest.raises(OllamaConnectionError):
            await agent.execute(
                category=AlgorithmCategory.EDGE_DETECTION,
                pipeline=sample_pipeline,
                plan=sample_plan,
            )

    @pytest.mark.anyio
    async def test_empty_response_triggers_retry(self, sample_pipeline, sample_plan):
        client = MagicMock()
        good_response = json.dumps({
            "code": "def inspect_item(image): return {'result': 'OK', 'details': {}}",
            "explanation": "빈 응답 후 재시도입니다.",
        })
        client.generate = AsyncMock(side_effect=["", good_response])
        agent = AlgorithmCoderInspection(ollama_client=client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result, AlgorithmResult)
        assert client.generate.call_count == 2


# ── 6. Directive Tests ────────────────────────────────────────────────────

class TestDirective:
    @pytest.mark.anyio
    async def test_directive_included_in_prompt(self, sample_pipeline, sample_plan):
        captured = []
        async def cap_generate(prompt, system=None):
            captured.append(prompt)
            return json.dumps({
                "code": "def inspect_item(image): return {'result': 'OK', 'details': {}}",
                "explanation": "지시사항 포함 테스트입니다.",
            })
        client = MagicMock()
        client.generate = cap_generate
        agent = AlgorithmCoderInspection(ollama_client=client, directive="엄격한 검사 필요")
        await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert any("엄격한 검사 필요" in p for p in captured)

    @pytest.mark.anyio
    async def test_no_directive_not_in_prompt(self, sample_pipeline, sample_plan):
        captured = []
        async def cap_generate(prompt, system=None):
            captured.append(prompt)
            return json.dumps({
                "code": "def inspect_item(image): return {'result': 'OK', 'details': {}}",
                "explanation": "지시 없음 테스트입니다.",
            })
        client = MagicMock()
        client.generate = cap_generate
        agent = AlgorithmCoderInspection(ollama_client=client)
        await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        for p in captured:
            assert "Additional directive" not in p


# ── 7. Edge Cases ─────────────────────────────────────────────────────────

class TestEdgeCases:
    @pytest.mark.anyio
    async def test_single_item_plan(self, mock_client, sample_pipeline, sample_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=sample_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result, AlgorithmResult)
        assert result.code != ""

    @pytest.mark.anyio
    async def test_five_item_plan_all_coded(self, mock_client, sample_pipeline, multi_item_plan):
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.BLOB,
            pipeline=sample_pipeline,
            plan=multi_item_plan,
        )
        assert isinstance(result, AlgorithmResult)
        assert mock_client.generate.call_count == 5

    @pytest.mark.anyio
    async def test_empty_pipeline_blocks(self, mock_client, sample_plan):
        empty_pipeline = ProcessingPipeline(name="empty", blocks=[], score=0.0)
        agent = AlgorithmCoderInspection(ollama_client=mock_client)
        result = await agent.execute(
            category=AlgorithmCategory.EDGE_DETECTION,
            pipeline=empty_pipeline,
            plan=sample_plan,
        )
        assert isinstance(result, AlgorithmResult)
