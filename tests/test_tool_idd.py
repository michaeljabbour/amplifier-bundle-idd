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
    async def test_returns_result_with_success_and_output(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({"input": "Add caching"})
        assert hasattr(result, "success")
        assert hasattr(result, "output")

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_valid_input_returns_json_decomposition(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({"input": "Add caching"})
        assert result.success is True
        # Output should be valid JSON containing the decomposition
        parsed = json.loads(result.output)
        assert "intent" in parsed
        assert parsed["intent"]["goal"] == "Add caching to the API layer"

    @pytest.mark.asyncio
    async def test_empty_input_returns_error(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({"input": ""})
        assert result.success is False
        assert "No input" in result.output

    @pytest.mark.asyncio
    async def test_missing_input_key_returns_error(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        result = await tool.execute({})
        assert result.success is False
        assert "No input" in result.output

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
        assert result.success is False
        assert "No decomposition" in result.output

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
        assert result.success is True
        assert isinstance(result.output, str)
        # Should be valid YAML containing recipe keys
        assert "name:" in result.output or "steps:" in result.output


# ===================================================================
# idd:composition_ready emission
# ===================================================================


class TestCompositionReadyEvent:
    """The decompose tool emits idd:composition_ready with a plan summary."""

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_emits_composition_ready(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        events = [e["event"] for e in coord.hooks._emitted]
        assert "idd:composition_ready" in events

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_composition_ready_has_plan_key(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        assert len(ready_events) == 1
        data = ready_events[0]["data"]
        assert "plan" in data
        assert isinstance(data["plan"], str)
        assert len(data["plan"]) > 0

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_composition_ready_has_decomposition(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        data = ready_events[0]["data"]
        assert "decomposition" in data
        assert data["decomposition"]["intent"]["goal"] == "Add caching to the API layer"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_plan_contains_goal(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        plan = ready_events[0]["data"]["plan"]
        assert "Add caching to the API layer" in plan

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_plan_contains_agents(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        plan = ready_events[0]["data"]["plan"]
        assert "explorer" in plan
        assert "zen-architect" in plan
        assert "builder" in plan

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_plan_contains_success_criteria(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        plan = ready_events[0]["data"]["plan"]
        assert "Response time < 200ms" in plan
        assert "Cache hit ratio > 80%" in plan

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_plan_contains_confidence(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        plan = ready_events[0]["data"]["plan"]
        assert "85%" in plan

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_emits_after_intent_parsed(self):
        """composition_ready must come after intent_parsed in event order."""
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        events = [e["event"] for e in coord.hooks._emitted]
        parsed_idx = events.index("idd:intent_parsed")
        ready_idx = events.index("idd:composition_ready")
        assert ready_idx > parsed_idx

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_plan_contains_scope_out(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        ready_events = [e for e in coord.hooks._emitted if e["event"] == "idd:composition_ready"]
        plan = ready_events[0]["data"]["plan"]
        assert "Database schema changes" in plan


# ===================================================================
# _build_plan_summary (direct tests)
# ===================================================================


class TestBuildPlanSummary:
    """Direct tests for the plan summary builder."""

    def test_minimal_decomposition(self):
        from amplifier_module_tool_idd import _build_plan_summary
        from amplifier_module_tool_idd.grammar import (
            AgentAssignment,
            ContextRequirement,
            Decomposition,
            IntentPrimitive,
            TriggerPrimitive,
        )

        d = Decomposition(
            intent=IntentPrimitive(goal="Test goal", success_criteria=["criterion 1"]),
            trigger=TriggerPrimitive(activation="user request"),
            agents=[AgentAssignment(name="self", role="executor", instruction="do it")],
            context=ContextRequirement(),
            behaviors=[],
            confidence=0.7,
        )
        plan = _build_plan_summary(d)
        assert "Test goal" in plan
        assert "self" in plan
        assert "criterion 1" in plan
        assert "70%" in plan

    def test_human_confirmation_shown(self):
        from amplifier_module_tool_idd import _build_plan_summary
        from amplifier_module_tool_idd.grammar import (
            AgentAssignment,
            ContextRequirement,
            Decomposition,
            IntentPrimitive,
            TriggerPrimitive,
        )

        d = Decomposition(
            intent=IntentPrimitive(goal="Delete data", success_criteria=[]),
            trigger=TriggerPrimitive(activation="user request", confirmation="human"),
            agents=[AgentAssignment(name="self", role="executor", instruction="delete")],
            context=ContextRequirement(),
            behaviors=[],
            confidence=0.9,
        )
        plan = _build_plan_summary(d)
        assert "human approval" in plan.lower()

    def test_no_scope_out_omitted(self):
        from amplifier_module_tool_idd import _build_plan_summary
        from amplifier_module_tool_idd.grammar import (
            AgentAssignment,
            ContextRequirement,
            Decomposition,
            IntentPrimitive,
            TriggerPrimitive,
        )

        d = Decomposition(
            intent=IntentPrimitive(goal="Simple task", success_criteria=[], scope_out=[]),
            trigger=TriggerPrimitive(activation="user request"),
            agents=[AgentAssignment(name="self", role="executor", instruction="go")],
            context=ContextRequirement(),
            behaviors=[],
            confidence=0.5,
        )
        plan = _build_plan_summary(d)
        assert "Out of scope" not in plan


# ===================================================================
# steps_total set after decompose (P0-3)
# ===================================================================


class TestStepsTotal:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_steps_total_equals_agent_count(self):
        coord = _coordinator_with_provider()
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        # VALID_DECOMPOSITION_JSON has 3 agents
        assert gs.steps_total == 3


# ===================================================================
# Callable capabilities registered via mount() (P1-2, P1-3, P2-1)
# ===================================================================


class TestCapabilitiesRegistered:
    @pytest.mark.asyncio
    async def test_mount_registers_decompose_capability(self):
        coord = FakeCoordinator()
        await mount(coord)
        cap = coord.get_capability("idd.decompose")
        assert cap is not None
        assert callable(cap)

    @pytest.mark.asyncio
    async def test_mount_registers_compile_capability(self):
        coord = FakeCoordinator()
        await mount(coord)
        cap = coord.get_capability("idd.compile")
        assert cap is not None
        assert callable(cap)

    @pytest.mark.asyncio
    async def test_mount_registers_update_criterion_capability(self):
        coord = FakeCoordinator()
        await mount(coord)
        cap = coord.get_capability("idd.update_criterion")
        assert cap is not None
        assert callable(cap)

    @pytest.mark.asyncio
    async def test_mount_registers_resolve_intent_capability(self):
        coord = FakeCoordinator()
        await mount(coord)
        cap = coord.get_capability("idd.resolve_intent")
        assert cap is not None
        assert callable(cap)


class TestUpdateCriterionCapability:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_update_criterion_marks_pass(self):
        coord = _coordinator_with_provider()
        await mount(coord)  # registers capabilities

        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})  # registers grammar_state

        update_fn = coord.get_capability("idd.update_criterion")
        assert update_fn is not None
        update_fn("Response time < 200ms", True, "Measured 150ms")

        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        criterion = next(c for c in gs.criteria_status if c.name == "Response time < 200ms")
        assert criterion.passed is True
        assert criterion.evidence == "Measured 150ms"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_update_criterion_marks_fail(self):
        coord = _coordinator_with_provider()
        await mount(coord)

        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        update_fn = coord.get_capability("idd.update_criterion")
        assert update_fn is not None
        update_fn("Cache hit ratio > 80%", False, "Only 60%")

        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        criterion = next(c for c in gs.criteria_status if c.name == "Cache hit ratio > 80%")
        assert criterion.passed is False
        assert criterion.evidence == "Only 60%"

    @pytest.mark.asyncio
    async def test_update_criterion_noop_when_no_grammar_state(self):
        """Should not crash if no grammar state is registered."""
        coord = FakeCoordinator()
        await mount(coord)
        update_fn = coord.get_capability("idd.update_criterion")
        assert update_fn is not None
        # Should not raise — just silently return
        update_fn("nonexistent", True, "")


class TestResolveIntentCapability:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_resolve_intent_emits_event(self):
        coord = _coordinator_with_provider()
        await mount(coord)
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        resolve_fn = coord.get_capability("idd.resolve_intent")
        assert resolve_fn is not None
        await resolve_fn("completed", "All done")

        resolved_events = [e for e in coord.hooks._emitted if e["event"] == "idd:intent_resolved"]
        assert len(resolved_events) == 1
        data = resolved_events[0]["data"]
        assert data["status"] == "completed"
        assert data["summary"] == "All done"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_resolve_intent_uses_goal_as_default_summary(self):
        coord = _coordinator_with_provider()
        await mount(coord)
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        resolve_fn = coord.get_capability("idd.resolve_intent")
        assert resolve_fn is not None
        await resolve_fn("completed")

        resolved_events = [e for e in coord.hooks._emitted if e["event"] == "idd:intent_resolved"]
        assert resolved_events[0]["data"]["summary"] == "Add caching to the API layer"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_resolve_intent_includes_criteria(self):
        coord = _coordinator_with_provider()
        await mount(coord)
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        # Mark one criterion
        update_fn = coord.get_capability("idd.update_criterion")
        assert update_fn is not None
        update_fn("Response time < 200ms", True, "150ms measured")

        resolve_fn = coord.get_capability("idd.resolve_intent")
        assert resolve_fn is not None
        await resolve_fn("completed")

        resolved_events = [e for e in coord.hooks._emitted if e["event"] == "idd:intent_resolved"]
        criteria = resolved_events[0]["data"]["success_criteria"]
        assert len(criteria) == 2
        assert criteria[0]["name"] == "Response time < 200ms"
        assert criteria[0]["pass"] is True

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_resolve_intent_sets_grammar_status(self):
        coord = _coordinator_with_provider()
        await mount(coord)
        tool = IDDDecomposeTool(coord)
        await tool.execute({"input": "Add caching"})

        resolve_fn = coord.get_capability("idd.resolve_intent")
        assert resolve_fn is not None
        await resolve_fn("failed", "Timed out")

        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert gs.status == "failed"

    @pytest.mark.asyncio
    async def test_resolve_intent_noop_when_no_grammar_state(self):
        """Should not crash if no grammar state is registered."""
        coord = FakeCoordinator()
        await mount(coord)
        resolve_fn = coord.get_capability("idd.resolve_intent")
        assert resolve_fn is not None
        # Should not raise
        await resolve_fn("completed", "no-op")


# ===================================================================
# Progress tracking hook (P0-3)
# ===================================================================


class TestProgressTracking:
    @pytest.mark.asyncio
    async def test_tool_post_hook_registered(self):
        coord = FakeCoordinator()
        await mount(coord)
        handlers = coord.hooks._handlers.get("tool:post", [])
        assert len(handlers) == 1
        assert handlers[0]["name"] == "idd-progress-tracker"
        assert handlers[0]["priority"] == 20

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_progress_emitted_on_tool_post(self):
        coord = _coordinator_with_provider()
        await mount(coord)

        # First decompose to create grammar state
        decompose_tool = IDDDecomposeTool(coord)
        await decompose_tool.execute({"input": "Add caching"})

        # Clear emitted events so we only see the progress event
        coord.hooks._emitted.clear()

        # Simulate a tool:post event
        await coord.hooks.emit("tool:post", {"tool_name": "read_file"})

        progress_events = [e for e in coord.hooks._emitted if e["event"] == "idd:progress"]
        assert len(progress_events) == 1
        assert progress_events[0]["data"]["step"] == "read_file"
        assert progress_events[0]["data"]["completed"] == 1
        assert progress_events[0]["data"]["total"] == 3

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_idd_tools_not_counted_as_progress(self):
        coord = _coordinator_with_provider()
        await mount(coord)

        decompose_tool = IDDDecomposeTool(coord)
        await decompose_tool.execute({"input": "Add caching"})

        coord.hooks._emitted.clear()

        # Simulate idd_ tool post — should NOT emit progress
        await coord.hooks.emit("tool:post", {"tool_name": "idd_compile"})

        progress_events = [e for e in coord.hooks._emitted if e["event"] == "idd:progress"]
        assert len(progress_events) == 0

    @pytest.mark.asyncio
    async def test_no_progress_without_grammar_state(self):
        coord = FakeCoordinator()
        await mount(coord)

        coord.hooks._emitted.clear()
        await coord.hooks.emit("tool:post", {"tool_name": "read_file"})

        progress_events = [e for e in coord.hooks._emitted if e["event"] == "idd:progress"]
        assert len(progress_events) == 0

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_progress_increments_steps_completed(self):
        coord = _coordinator_with_provider()
        await mount(coord)

        decompose_tool = IDDDecomposeTool(coord)
        await decompose_tool.execute({"input": "Add caching"})

        gs = coord.get_capability("idd.grammar_state")
        assert gs.steps_completed == 0

        await coord.hooks.emit("tool:post", {"tool_name": "read_file"})
        assert gs.steps_completed == 1

        await coord.hooks.emit("tool:post", {"tool_name": "write_file"})
        assert gs.steps_completed == 2

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_progress_sets_status_to_executing(self):
        coord = _coordinator_with_provider()
        await mount(coord)

        decompose_tool = IDDDecomposeTool(coord)
        await decompose_tool.execute({"input": "Add caching"})

        gs = coord.get_capability("idd.grammar_state")
        assert gs.status == "decomposed"

        await coord.hooks.emit("tool:post", {"tool_name": "read_file"})
        assert gs.status == "executing"
