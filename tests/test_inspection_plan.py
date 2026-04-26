"""Tests for InspectionPlanAgent and inspection_plan_prompt module (Step 18)."""
from __future__ import annotations

import inspect
import json
from unittest.mock import AsyncMock, patch

import pytest

from agents.base_agent import BaseAgent
from agents.models import AlgorithmCategory, InspectionItem, InspectionPlan
from agents.prompts.inspection_plan_prompt import (
    INSPECTION_PLAN_SYSTEM_PROMPT,
    build_inspection_plan_prompt,
)
from agents.inspection_plan_agent import InspectionPlanAgent
from backend.services.ollama_client import OllamaConnectionError, OllamaError


# ── helpers ───────────────────────────────────────────────────────────────────

def _item_dict(id: int, name: str, method: str = "BLOB", depends_on: list | None = None) -> dict:
    return {
        "id": id,
        "name": name,
        "purpose": f"Purpose of {name}",
        "method": method,
        "depends_on": depends_on or [],
        "safety_role": "기초 검출",
        "success_criteria": f"{name} succeeded",
    }


def _response(*items: dict) -> str:
    return json.dumps({"items": list(items)})


# ── Prompt module: system prompt ──────────────────────────────────────────────

class TestInspectionPlanSystemPrompt:
    def test_is_string(self):
        assert isinstance(INSPECTION_PLAN_SYSTEM_PROMPT, str)

    def test_is_non_empty(self):
        assert len(INSPECTION_PLAN_SYSTEM_PROMPT) > 0

    def test_length_over_100(self):
        assert len(INSPECTION_PLAN_SYSTEM_PROMPT) > 100

    def test_contains_inspection(self):
        assert "inspection" in INSPECTION_PLAN_SYSTEM_PROMPT.lower()

    def test_contains_items(self):
        assert "items" in INSPECTION_PLAN_SYSTEM_PROMPT

    def test_contains_depends_on(self):
        assert "depends_on" in INSPECTION_PLAN_SYSTEM_PROMPT

    def test_contains_safety_role(self):
        assert "safety_role" in INSPECTION_PLAN_SYSTEM_PROMPT

    def test_contains_method(self):
        assert "method" in INSPECTION_PLAN_SYSTEM_PROMPT

    def test_contains_json_instruction(self):
        assert "json" in INSPECTION_PLAN_SYSTEM_PROMPT.lower()

    def test_contains_all_algorithm_category_values(self):
        for val in ("BLOB", "COLOR_FILTER", "EDGE_DETECTION", "TEMPLATE_MATCHING"):
            assert val in INSPECTION_PLAN_SYSTEM_PROMPT, f"Missing AlgorithmCategory: {val}"


# ── Prompt module: build function ─────────────────────────────────────────────

class TestBuildInspectionPlanPrompt:
    def test_includes_purpose(self):
        result = build_inspection_plan_prompt("solder defect detection", "bright image")
        assert "solder defect detection" in result

    def test_includes_diagnosis_summary(self):
        result = build_inspection_plan_prompt("scratch detection", "high contrast, low noise")
        assert "high contrast, low noise" in result

    def test_with_directive_includes_directive_text(self):
        result = build_inspection_plan_prompt("purpose", "summary", directive="use BLOB only")
        assert "use BLOB only" in result

    def test_with_directive_longer_than_without(self):
        without = build_inspection_plan_prompt("purpose", "summary")
        with_d = build_inspection_plan_prompt("purpose", "summary", directive="extra guidance")
        assert len(with_d) > len(without)

    def test_without_directive_lacks_directive_text(self):
        result = build_inspection_plan_prompt("purpose", "summary")
        assert "extra guidance" not in result


# ── Class structure ───────────────────────────────────────────────────────────

class TestInspectionPlanAgentStructure:
    def test_is_subclass_of_base_agent(self):
        assert issubclass(InspectionPlanAgent, BaseAgent)

    def test_agent_name(self):
        assert InspectionPlanAgent().agent_name == "inspection_plan"

    def test_execute_is_coroutine(self):
        assert inspect.iscoroutinefunction(InspectionPlanAgent().execute)

    def test_constructor_accepts_directive(self):
        agent = InspectionPlanAgent(directive="test directive")
        assert agent.get_directive() == "test directive"

    def test_set_directive_works(self):
        agent = InspectionPlanAgent()
        agent.set_directive("new directive")
        assert agent.get_directive() == "new directive"


# ── Execute: core behaviour ───────────────────────────────────────────────────

class TestInspectionPlanAgentExecute:
    @pytest.mark.asyncio
    async def test_returns_inspection_plan(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Edge Check")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("find defects", "normal image")
        assert isinstance(result, InspectionPlan)
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_items_are_inspection_items(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Blob Step", method="BLOB")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert all(isinstance(item, InspectionItem) for item in result.items)

    @pytest.mark.asyncio
    async def test_item_field_types(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(
            return_value=_response(_item_dict(1, "Step One", method="EDGE_DETECTION"))
        )
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        item = result.items[0]
        assert isinstance(item.id, int)
        assert isinstance(item.name, str)
        assert isinstance(item.method, AlgorithmCategory)
        assert isinstance(item.depends_on, list)

    @pytest.mark.asyncio
    async def test_calls_generate_with_system_prompt(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Step")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            await agent.execute("purpose", "summary")
        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs.get("system") == INSPECTION_PLAN_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_purpose_appears_in_prompt(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Step")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            await agent.execute("unique_purpose_xyz", "summary")
        assert "unique_purpose_xyz" in mock_gen.call_args.args[0]

    @pytest.mark.asyncio
    async def test_diagnosis_summary_appears_in_prompt(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Step")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            await agent.execute("purpose", "unique_summary_abc")
        assert "unique_summary_abc" in mock_gen.call_args.args[0]

    @pytest.mark.asyncio
    async def test_directive_in_prompt_when_set(self):
        agent = InspectionPlanAgent(directive="unique_directive_123")
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Step")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            await agent.execute("purpose", "summary")
        assert "unique_directive_123" in mock_gen.call_args.args[0]

    @pytest.mark.asyncio
    async def test_multiple_items_with_depends_on(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(
            _item_dict(1, "Step A"),
            _item_dict(2, "Step B", depends_on=[1]),
            _item_dict(3, "Step C", depends_on=[1, 2]),
        ))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert len(result.items) == 3
        assert result.items[1].depends_on == [1]
        assert result.items[2].depends_on == [1, 2]


# ── Dependency validation ─────────────────────────────────────────────────────

class TestDependencyValidation:
    @pytest.mark.asyncio
    async def test_valid_depends_on_passes(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(
            _item_dict(1, "A"),
            _item_dict(2, "B", depends_on=[1]),
        ))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert result.items[1].depends_on == [1]

    @pytest.mark.asyncio
    async def test_invalid_reference_removed_with_warning(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "A", depends_on=[99])))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            with patch.object(agent, "_log") as mock_log:
                result = await agent.execute("purpose", "summary")
        assert 99 not in result.items[0].depends_on
        warnings = [c for c in mock_log.call_args_list if c.args[0] == "WARNING"]
        assert len(warnings) > 0

    @pytest.mark.asyncio
    async def test_self_reference_removed(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "A", depends_on=[1])))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert 1 not in result.items[0].depends_on

    @pytest.mark.asyncio
    async def test_forward_reference_removed(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(
            _item_dict(1, "A", depends_on=[2]),
            _item_dict(2, "B"),
        ))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert 2 not in result.items[0].depends_on


# ── Method validation ─────────────────────────────────────────────────────────

class TestMethodValidation:
    @pytest.mark.asyncio
    async def test_all_valid_methods_pass_through(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(
            _item_dict(1, "A", method="BLOB"),
            _item_dict(2, "B", method="COLOR_FILTER"),
            _item_dict(3, "C", method="EDGE_DETECTION"),
            _item_dict(4, "D", method="TEMPLATE_MATCHING"),
        ))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        methods = {item.method for item in result.items}
        assert methods == {
            AlgorithmCategory.BLOB,
            AlgorithmCategory.COLOR_FILTER,
            AlgorithmCategory.EDGE_DETECTION,
            AlgorithmCategory.TEMPLATE_MATCHING,
        }

    @pytest.mark.asyncio
    async def test_invalid_method_defaults_to_blob_with_warning(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "A", method="INVALID_METHOD")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            with patch.object(agent, "_log") as mock_log:
                result = await agent.execute("purpose", "summary")
        assert result.items[0].method == AlgorithmCategory.BLOB
        warnings = [c for c in mock_log.call_args_list if c.args[0] == "WARNING"]
        assert len(warnings) > 0

    @pytest.mark.asyncio
    async def test_lowercase_method_defaults_to_blob(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "A", method="blob")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert result.items[0].method == AlgorithmCategory.BLOB


# ── JSON parsing robustness ───────────────────────────────────────────────────

class TestJsonParsingRobustness:
    @pytest.mark.asyncio
    async def test_markdown_code_fence_stripped(self):
        agent = InspectionPlanAgent()
        raw_json = json.dumps({"items": [_item_dict(1, "Step")]})
        fenced = f"```json\n{raw_json}\n```"
        mock_gen = AsyncMock(return_value=fenced)
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert isinstance(result, InspectionPlan)
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_plain_json_works(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Step")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert isinstance(result, InspectionPlan)

    @pytest.mark.asyncio
    async def test_first_attempt_fails_retry_succeeds(self):
        agent = InspectionPlanAgent()
        valid = _response(_item_dict(1, "Step"))
        mock_gen = AsyncMock(side_effect=["not valid json {{{{", valid])
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert isinstance(result, InspectionPlan)
        assert mock_gen.call_count == 2

    @pytest.mark.asyncio
    async def test_both_attempts_fail_raises_value_error(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value="not valid json {{{{{")
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            with pytest.raises(ValueError):
                await agent.execute("purpose", "summary")
        assert mock_gen.call_count == 2


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_ollama_error_propagates(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(side_effect=OllamaError("connection failed"))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            with pytest.raises(OllamaError):
                await agent.execute("purpose", "summary")

    @pytest.mark.asyncio
    async def test_ollama_connection_error_propagates(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(side_effect=OllamaConnectionError("cannot connect"))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            with pytest.raises(OllamaConnectionError):
                await agent.execute("purpose", "summary")

    @pytest.mark.asyncio
    async def test_empty_items_triggers_retry(self):
        agent = InspectionPlanAgent()
        empty = json.dumps({"items": []})
        valid = _response(_item_dict(1, "Step"))
        mock_gen = AsyncMock(side_effect=[empty, valid])
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert isinstance(result, InspectionPlan)
        assert len(result.items) >= 1
        assert mock_gen.call_count == 2


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_single_item_no_dependencies(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(_item_dict(1, "Only Step")))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert len(result.items) == 1
        assert result.items[0].depends_on == []

    @pytest.mark.asyncio
    async def test_complex_dependency_chain(self):
        agent = InspectionPlanAgent()
        mock_gen = AsyncMock(return_value=_response(
            _item_dict(1, "A"),
            _item_dict(2, "B", depends_on=[1]),
            _item_dict(3, "C", depends_on=[1, 2]),
            _item_dict(4, "D", depends_on=[2, 3]),
            _item_dict(5, "E", depends_on=[1, 2, 3, 4]),
        ))
        with patch("agents.inspection_plan_agent.ollama_client.generate", new=mock_gen):
            result = await agent.execute("purpose", "summary")
        assert len(result.items) == 5
        assert result.items[4].depends_on == [1, 2, 3, 4]
