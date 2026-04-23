"""Tests for Step 12: Spec Agent implementation."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from agents.base_agent import BaseAgent
from agents.models import InspectionMode, SpecResult
from agents.prompts.spec_prompt import SPEC_SYSTEM_PROMPT, build_spec_prompt
from agents.spec_agent import SpecAgent


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


def _make_response(mode: str = "inspection", goal: str = "검출", criteria: dict | None = None) -> str:
    return json.dumps({
        "mode": mode,
        "goal": goal,
        "success_criteria": criteria if criteria is not None else {},
    })


# ── Class structure ──────────────────────────────────────────────────────────

class TestSpecAgentClass:
    def test_inherits_base_agent(self):
        agent = SpecAgent()
        assert isinstance(agent, BaseAgent)

    def test_agent_name_is_spec(self):
        agent = SpecAgent()
        assert agent.agent_name == "spec"

    def test_no_directive_by_default(self):
        agent = SpecAgent()
        assert agent.get_directive() is None

    def test_directive_stored(self):
        agent = SpecAgent(directive="focus on edges")
        assert agent.get_directive() == "focus on edges"


# ── Prompt template ──────────────────────────────────────────────────────────

class TestSpecPrompt:
    def test_build_spec_prompt_contains_user_text(self):
        prompt = build_spec_prompt("find scratches on metal surface")
        assert "find scratches on metal surface" in prompt

    def test_build_spec_prompt_without_directive(self):
        prompt = build_spec_prompt("test text")
        assert prompt
        assert "be extra strict" not in prompt

    def test_build_spec_prompt_with_directive_included(self):
        prompt = build_spec_prompt("test text", directive="be extra strict")
        assert "be extra strict" in prompt

    def test_build_spec_prompt_no_directive_returns_string(self):
        result = build_spec_prompt("검사해줘", directive=None)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_system_prompt_mentions_both_modes(self):
        assert "inspection" in SPEC_SYSTEM_PROMPT
        assert "align" in SPEC_SYSTEM_PROMPT

    def test_system_prompt_instructs_json_output(self):
        assert "JSON" in SPEC_SYSTEM_PROMPT or "json" in SPEC_SYSTEM_PROMPT

    def test_system_prompt_lists_inspection_criteria_fields(self):
        assert "accuracy" in SPEC_SYSTEM_PROMPT
        assert "fp_rate" in SPEC_SYSTEM_PROMPT
        assert "fn_rate" in SPEC_SYSTEM_PROMPT

    def test_system_prompt_lists_align_criteria_fields(self):
        assert "coord_error" in SPEC_SYSTEM_PROMPT
        assert "success_rate" in SPEC_SYSTEM_PROMPT

    def test_system_prompt_mentions_goal_field(self):
        assert "goal" in SPEC_SYSTEM_PROMPT


# ── execute() core behavior ──────────────────────────────────────────────────

class TestSpecAgentExecute:
    @pytest.mark.anyio
    async def test_execute_inspection_returns_spec_result(self):
        agent = SpecAgent()
        criteria = {"accuracy": 0.98, "fp_rate": 0.02, "fn_rate": 0.02}
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response(
                mode="inspection", goal="스크래치 검출", criteria=criteria
            ))
            result = await agent.execute(user_text="금속 표면 스크래치 찾아줘")

        assert isinstance(result, SpecResult)
        assert result.mode == InspectionMode.inspection
        assert result.goal == "스크래치 검출"
        assert result.success_criteria["accuracy"] == 0.98

    @pytest.mark.anyio
    async def test_execute_align_returns_spec_result(self):
        agent = SpecAgent()
        criteria = {"coord_error": 1.5, "success_rate": 0.95}
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response(
                mode="align", goal="부품 정렬", criteria=criteria
            ))
            result = await agent.execute(user_text="부품 정렬해줘")

        assert isinstance(result, SpecResult)
        assert result.mode == InspectionMode.align
        assert result.goal == "부품 정렬"
        assert result.success_criteria["coord_error"] == 1.5

    @pytest.mark.anyio
    async def test_execute_korean_input_parsed_correctly(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response(
                mode="inspection", goal="이물질 검출", criteria={"accuracy": 0.90}
            ))
            result = await agent.execute(user_text="PCB 기판의 이물질을 검출해줘")

        assert result.goal == "이물질 검출"
        assert result.mode == InspectionMode.inspection

    @pytest.mark.anyio
    async def test_execute_calls_generate_with_system_prompt(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response())
            await agent.execute(user_text="find defects")

            mock_client.generate.assert_called_once()
            call_kwargs = mock_client.generate.call_args
            system_arg = (
                call_kwargs.kwargs.get("system")
                if call_kwargs.kwargs.get("system") is not None
                else (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
            )
            assert system_arg == SPEC_SYSTEM_PROMPT

    @pytest.mark.anyio
    async def test_execute_with_directive_includes_directive_in_prompt(self):
        agent = SpecAgent(directive="be very strict about accuracy")
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response())
            await agent.execute(user_text="find defects")

            call_kwargs = mock_client.generate.call_args
            prompt_arg = (
                call_kwargs.args[0]
                if call_kwargs.args
                else call_kwargs.kwargs.get("prompt")
            )
            assert "be very strict about accuracy" in prompt_arg


# ── Default values for missing success_criteria ──────────────────────────────

class TestSpecAgentDefaults:
    @pytest.mark.anyio
    async def test_missing_accuracy_gets_inspection_default(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response(
                mode="inspection", criteria={}
            ))
            result = await agent.execute(user_text="find defects")

        assert result.success_criteria["accuracy"] == 0.95
        assert result.success_criteria["fp_rate"] == 0.05
        assert result.success_criteria["fn_rate"] == 0.05

    @pytest.mark.anyio
    async def test_partial_inspection_criteria_fills_missing(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response(
                mode="inspection", criteria={"accuracy": 0.99}
            ))
            result = await agent.execute(user_text="find defects")

        assert result.success_criteria["accuracy"] == 0.99
        assert result.success_criteria["fp_rate"] == 0.05
        assert result.success_criteria["fn_rate"] == 0.05

    @pytest.mark.anyio
    async def test_missing_align_criteria_gets_align_defaults(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=_make_response(
                mode="align", criteria={}
            ))
            result = await agent.execute(user_text="align parts")

        assert result.success_criteria["coord_error"] == 2.0
        assert result.success_criteria["success_rate"] == 0.9

    @pytest.mark.anyio
    async def test_unrecognized_mode_defaults_to_inspection(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=json.dumps({
                "mode": "unknown_mode",
                "goal": "검출",
                "success_criteria": {},
            }))
            result = await agent.execute(user_text="find defects")

        assert result.mode == InspectionMode.inspection


# ── JSON parsing robustness ──────────────────────────────────────────────────

class TestSpecAgentJsonParsing:
    @pytest.mark.anyio
    async def test_json_wrapped_in_markdown_code_block(self):
        agent = SpecAgent()
        wrapped = '```json\n' + _make_response() + '\n```'
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=wrapped)
            result = await agent.execute(user_text="find defects")

        assert isinstance(result, SpecResult)

    @pytest.mark.anyio
    async def test_json_wrapped_in_plain_code_block(self):
        agent = SpecAgent()
        wrapped = '```\n' + _make_response() + '\n```'
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value=wrapped)
            result = await agent.execute(user_text="find defects")

        assert isinstance(result, SpecResult)

    @pytest.mark.anyio
    async def test_malformed_json_triggers_retry(self):
        agent = SpecAgent()
        valid = _make_response()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(side_effect=["not valid json {{{", valid])
            result = await agent.execute(user_text="find defects")

        assert mock_client.generate.call_count == 2
        assert isinstance(result, SpecResult)

    @pytest.mark.anyio
    async def test_two_malformed_responses_raises_value_error(self):
        agent = SpecAgent()
        with patch("agents.spec_agent.ollama_client") as mock_client:
            mock_client.generate = AsyncMock(return_value="totally broken {{{")
            with pytest.raises(ValueError):
                await agent.execute(user_text="find defects")

        assert mock_client.generate.call_count == 2
