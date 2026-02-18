"""Tests for the IDD Orchestrator module."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from amplifier_module_orchestrator_idd import IDDOrchestrator, mount
from amplifier_module_orchestrator_idd.grammar import GrammarState
from amplifier_module_orchestrator_idd.parser import IDDParser

from helpers import (
    VALID_DECOMPOSITION_JSON,
    FakeContextManager,
    FakeCoordinator,
    FakeHookRegistry,
    FakeProvider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patched_build_request(self, prompt, available_agents):
    """Bypass ChatRequest/ChatMessage dependency for testing."""
    return {"prompt": prompt, "agents": available_agents}


def _coordinator_with_agents(*agent_names: str) -> FakeCoordinator:
    agents = {name: {} for name in agent_names}
    return FakeCoordinator(config={"agents": agents})


def _providers(response: str = VALID_DECOMPOSITION_JSON) -> dict:
    return {"fake": FakeProvider(response)}


async def _run_orchestrator(
    prompt: str = "Add caching",
    coordinator: FakeCoordinator | None = None,
    providers: dict | None = None,
) -> tuple[str, FakeCoordinator, FakeHookRegistry]:
    """Run the full orchestrator lifecycle and return (result, coordinator, hooks)."""
    coord = coordinator or _coordinator_with_agents("explorer", "builder")
    hooks = coord.hooks
    provs = providers or _providers()
    ctx = FakeContextManager()

    orch = IDDOrchestrator(config=coord.config)
    result = await orch.execute(
        prompt=prompt,
        context=ctx,
        providers=provs,
        tools={},
        hooks=hooks,
        coordinator=coord,
    )
    return result, coord, hooks


# ===================================================================
# mount()
# ===================================================================


class TestMount:
    @pytest.mark.asyncio
    async def test_mount_registers_orchestrator(self):
        coord = FakeCoordinator()
        await mount(coord, {})
        assert "orchestrator" in coord._mounted
        assert isinstance(coord._mounted["orchestrator"], IDDOrchestrator)

    @pytest.mark.asyncio
    async def test_mount_default_config(self):
        coord = FakeCoordinator()
        await mount(coord)
        assert isinstance(coord._mounted["orchestrator"], IDDOrchestrator)


# ===================================================================
# execute() -- protocol compliance
# ===================================================================


class TestOrchestratorProtocol:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_execute_returns_string(self):
        result, _, _ = await _run_orchestrator()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_execute_result_contains_completion(self):
        result, _, _ = await _run_orchestrator()
        assert "IDD Execution Complete" in result


# ===================================================================
# Grammar state capability
# ===================================================================


class TestOrchestratorGrammarState:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_registers_grammar_state_capability(self):
        _, coord, _ = await _run_orchestrator()
        grammar_state = coord.get_capability("idd.grammar_state")
        assert grammar_state is not None
        assert isinstance(grammar_state, GrammarState)

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_grammar_state_has_decomposition(self):
        _, coord, _ = await _run_orchestrator()
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert gs.decomposition is not None
        assert gs.decomposition.intent.goal == "Add caching to the API layer"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_grammar_state_completed(self):
        _, coord, _ = await _run_orchestrator()
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert gs.status == "completed"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_grammar_state_tracks_steps(self):
        _, coord, _ = await _run_orchestrator()
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert gs.steps_total > 0
        assert gs.steps_completed == gs.steps_total

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_grammar_state_criteria_populated(self):
        _, coord, _ = await _run_orchestrator()
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert len(gs.criteria_status) == 2
        assert gs.criteria_status[0].name == "Response time < 200ms"


# ===================================================================
# Event emission
# ===================================================================


class TestOrchestratorEvents:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_emits_intent_parsed(self):
        _, _, hooks = await _run_orchestrator()
        event_names = [e["event"] for e in hooks._emitted]
        assert "idd:intent_parsed" in event_names

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_intent_parsed_has_decomposition(self):
        _, _, hooks = await _run_orchestrator()
        parsed_events = [e for e in hooks._emitted if e["event"] == "idd:intent_parsed"]
        assert len(parsed_events) == 1
        data = parsed_events[0]["data"]
        assert "decomposition" in data
        assert "raw_input" in data

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_emits_composition_ready(self):
        _, _, hooks = await _run_orchestrator()
        event_names = [e["event"] for e in hooks._emitted]
        assert "idd:composition_ready" in event_names

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_composition_ready_has_plan(self):
        _, _, hooks = await _run_orchestrator()
        ready_events = [e for e in hooks._emitted if e["event"] == "idd:composition_ready"]
        assert len(ready_events) == 1
        data = ready_events[0]["data"]
        assert "plan" in data
        assert len(data["plan"]) > 0

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_emits_intent_resolved(self):
        _, _, hooks = await _run_orchestrator()
        event_names = [e["event"] for e in hooks._emitted]
        assert "idd:intent_resolved" in event_names

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_intent_resolved_has_status(self):
        _, _, hooks = await _run_orchestrator()
        resolved = [e for e in hooks._emitted if e["event"] == "idd:intent_resolved"]
        assert len(resolved) == 1
        data = resolved[0]["data"]
        assert data["status"] == "completed"
        assert "results" in data
        assert "summary" in data

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_emits_progress_per_step(self):
        _, _, hooks = await _run_orchestrator()
        progress_events = [e for e in hooks._emitted if e["event"] == "idd:progress"]
        # The valid decomposition JSON has 3 agents -> 3 steps -> 3 progress events
        assert len(progress_events) == 3

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_progress_events_increment(self):
        _, _, hooks = await _run_orchestrator()
        progress_events = [e for e in hooks._emitted if e["event"] == "idd:progress"]
        completed_values = [e["data"]["completed"] for e in progress_events]
        assert completed_values == [1, 2, 3]

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_progress_has_step_name(self):
        _, _, hooks = await _run_orchestrator()
        progress_events = [e for e in hooks._emitted if e["event"] == "idd:progress"]
        for ev in progress_events:
            assert "step" in ev["data"]
            assert isinstance(ev["data"]["step"], str)


# ===================================================================
# Missing coordinator (kwargs edge case)
# ===================================================================


class TestOrchestratorNoCoordinator:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_handles_missing_coordinator(self):
        """Orchestrator should work even without a coordinator in kwargs."""
        hooks = FakeHookRegistry()
        ctx = FakeContextManager()
        provs = _providers()

        orch = IDDOrchestrator(config={})
        result = await orch.execute(
            prompt="No coordinator test",
            context=ctx,
            providers=provs,
            tools={},
            hooks=hooks,
            # no coordinator= keyword
        )
        assert isinstance(result, str)
        assert "IDD Execution Complete" in result


# ===================================================================
# Grammar state mutation during execution
# ===================================================================


class TestOrchestratorStateMutation:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_status_transitions(self):
        """Grammar state should end as 'completed' after successful execution."""
        _, coord, _ = await _run_orchestrator()
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert gs.status == "completed"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_steps_total_matches_recipe(self):
        _, coord, _ = await _run_orchestrator()
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        # 3 agents in VALID_DECOMPOSITION_JSON
        assert gs.steps_total == 3

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_single_agent_decomposition(self):
        """A decomposition with one agent should produce one step."""
        single_agent_json = json.dumps(
            {
                "intent": {"goal": "simple task", "success_criteria": ["done"]},
                "agents": [{"name": "self", "role": "exec", "instruction": "do it"}],
                "confidence": 0.5,
            }
        )
        result, coord, hooks = await _run_orchestrator(
            prompt="simple",
            providers=_providers(single_agent_json),
        )
        gs = coord.get_capability("idd.grammar_state")
        assert gs is not None
        assert gs.steps_total == 1
        assert gs.steps_completed == 1
        progress = [e for e in hooks._emitted if e["event"] == "idd:progress"]
        assert len(progress) == 1
