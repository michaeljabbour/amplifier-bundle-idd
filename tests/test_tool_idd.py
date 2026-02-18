"""Tests for the IDD Tool module (tool-idd)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from amplifier_module_tool_idd import IDDCompileTool, IDDDecomposeTool, mount
from amplifier_module_tool_idd.grammar import GrammarState
from amplifier_module_tool_idd.parser import IDDParser

from helpers import (
    VALID_DECOMPOSITION_JSON,
    FakeCoordinator,
    FakeProvider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patched_build_request(self, prompt, available_agents):
    """Bypass ChatRequest/ChatMessage dependency for testing."""
    return {"prompt": prompt, "agents": available_agents}


def _coordinator_with_provider(
    response: str = VALID_DECOMPOSITION_JSON,
) -> FakeCoordinator:
    """Build a FakeCoordinator wired with a single FakeProvider."""
    provider = FakeProvider(response)
    return FakeCoordinator(
        config={"agents": {"explorer": {}, "zen-architect": {}, "builder": {}}},
        providers={"fake": provider},
    )


# ===================================================================
# mount()
# ===================================================================


class TestMount:
    @pytest.mark.asyncio
    async def test_mount_registers_two_tools(self):
        coord = FakeCoordinator()
        await mount(coord, {})
        assert "tools" in coord._mounted
        assert "idd_decompose" in coord._mounted["tools"]
        assert "idd_compile" in coord._mounted["tools"]

    @pytest.mark.asyncio
    async def test_mount_registers_decompose_tool(self):
        coord = FakeCoordinator()
        await mount(coord)
        tool = coord._mounted["tools"]["idd_decompose"]
        assert isinstance(tool, IDDDecomposeTool)

    @pytest.mark.asyncio
    async def test_mount_registers_compile_tool(self):
        coord = FakeCoordinator()
        await mount(coord)
        tool = coord._mounted["tools"]["idd_compile"]
        assert isinstance(tool, IDDCompileTool)


# ===================================================================
# IDDDecomposeTool -- properties
# ===================================================================


class TestDecomposeToolProperties:
    def test_name(self):
        tool = IDDDecomposeTool(FakeCoordinator())
        assert tool.name == "idd_decompose"

    def test_description_not_empty(self):
        tool = IDDDecomposeTool(FakeCoordinator())
        assert isinstance(tool.description, str)
        assert len(tool.description) > 20

    def test_input_schema_requires_input(self):
        tool = IDDDecomposeTool(FakeCoordinator())
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "input" in schema["properties"]
        assert "input" in schema["required"]


# ===================================================================
# IDDDecomposeTool.execute()
# ===================================================================


class TestDecomposeToolExecute:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_returns_dict_with_success_and_output(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({"input": "Add caching"})
        assert isinstance(result, dict)
        assert "success" in result
        assert "output" in result

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_valid_input_returns_json_decomposition(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({"input": "Add caching"})
        assert result["success"] is True
        # Output should be valid JSON containing the decomposition
        parsed = json.loads(result["output"])
        assert "intent" in parsed
        assert parsed["intent"]["goal"] == "Add caching to the API layer"

    @pytest.mark.asyncio
    async def test_empty_input_returns_error(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({"input": ""})
        assert result["success"] is False
        assert "No input" in result["output"]

    @pytest.mark.asyncio
    async def test_missing_input_key_returns_error(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({})
        assert result["success"] is False
        assert "No input" in result["output"]

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_registers_grammar_state_capability(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        grammar_state = coord.get_capability("idd.grammar_state")
        assert grammar_state is not None
        assert isinstance(grammar_state, GrammarState)
        assert grammar_state.decomposition is not None
        assert grammar_state.status == "decomposed"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_grammar_state_has_criteria(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert len(gs.criteria_status) == 2
        assert gs.criteria_status[0].name == "Response time < 200ms"


# ===================================================================
# IDDCompileTool.execute()
# ===================================================================


class TestCompileToolExecute:
    @pytest.mark.asyncio
    async def test_no_prior_decomposition_returns_error(self):
        coord = FakeCoordinator()
        tool = IDDCompileTool(coord)
        result = await tool.execute({})
        assert result["success"] is False
        assert "No decomposition" in result["output"]

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_after_decompose_returns_yaml(self):
        coord = _coordinator_with_provider()

        # First decompose
        decompose_tool = IDDDecomposeTool(coord)
        await decompose_tool.execute({"input": "Add caching"})

        # Then compile
        compile_tool = IDDCompileTool(coord)
        result = await compile_tool.execute({})
        assert result["success"] is True
        assert isinstance(result["output"], str)
        # Should be valid YAML containing recipe keys
        assert "name:" in result["output"] or "steps:" in result["output"]
