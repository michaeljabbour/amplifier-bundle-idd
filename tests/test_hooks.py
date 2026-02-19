"""Tests for all three IDD hook modules."""

from __future__ import annotations

import pytest

from amplifier_module_tool_idd.grammar import (
    CorrectionRecord,
    Decomposition,
    GrammarState,
    IntentPrimitive,
    SuccessCriterionStatus,
    TriggerPrimitive,
    AgentAssignment,
    ContextRequirement,
)

from helpers import FakeCoordinator, FakeMemoryStore

from amplifier_module_hooks_idd_memory_bridge import (
    mount as memory_bridge_mount,
    IDDMemoryBridge,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _grammar_state_with_decomposition() -> GrammarState:
    """Build a GrammarState with a real decomposition attached."""
    return GrammarState(
        decomposition=Decomposition(
            intent=IntentPrimitive(
                goal="Add caching",
                success_criteria=["Response < 200ms", "Hit ratio > 80%"],
            ),
            trigger=TriggerPrimitive(activation="user request"),
            agents=[AgentAssignment(name="builder", role="impl", instruction="build it")],
            context=ContextRequirement(),
            behaviors=[],
            raw_input="Add caching",
            confidence=0.8,
        ),
        criteria_status=[
            SuccessCriterionStatus(name="Response < 200ms", passed=True),
            SuccessCriterionStatus(name="Hit ratio > 80%", passed=None),
        ],
        status="executing",
        steps_completed=1,
        steps_total=3,
    )


# ===================================================================
# IDDEventRecorder (hooks-idd-events)
# ===================================================================


class TestIDDEventRecorderMount:
    @pytest.mark.asyncio
    async def test_mount_registers_all_six_events(self):
        from amplifier_module_hooks_idd_events import mount, _IDD_EVENTS

        coord = FakeCoordinator()
        await mount(coord)

        for event in _IDD_EVENTS:
            assert event in coord.hooks._handlers, f"Handler not registered for {event}"
            assert len(coord.hooks._handlers[event]) == 1

    @pytest.mark.asyncio
    async def test_mount_registers_capability(self):
        from amplifier_module_hooks_idd_events import mount

        coord = FakeCoordinator()
        await mount(coord)
        event_log = coord.get_capability("idd.event_log")
        assert event_log is not None
        assert isinstance(event_log, list)

    @pytest.mark.asyncio
    async def test_cleanup_unregisters_all(self):
        from amplifier_module_hooks_idd_events import mount, _IDD_EVENTS

        coord = FakeCoordinator()
        cleanup = await mount(coord)

        # All events registered
        for event in _IDD_EVENTS:
            assert len(coord.hooks._handlers[event]) == 1

        # After cleanup, all gone
        cleanup()
        for event in _IDD_EVENTS:
            assert len(coord.hooks._handlers[event]) == 0


class TestIDDEventRecorderHandler:
    @pytest.mark.asyncio
    async def test_records_event(self):
        from amplifier_module_hooks_idd_events import IDDEventRecorder

        recorder = IDDEventRecorder(config={})
        result = await recorder.handle_event("idd:intent_parsed", {"goal": "test"})
        assert result.action == "continue"
        assert len(recorder._events) == 1
        assert recorder._events[0]["event"] == "idd:intent_parsed"

    @pytest.mark.asyncio
    async def test_records_multiple_events(self):
        from amplifier_module_hooks_idd_events import IDDEventRecorder

        recorder = IDDEventRecorder(config={})
        await recorder.handle_event("idd:intent_parsed", {"a": "1"})
        await recorder.handle_event("idd:progress", {"b": "2"})
        await recorder.handle_event("idd:intent_resolved", {"c": "3"})
        assert len(recorder._events) == 3

    @pytest.mark.asyncio
    async def test_event_has_timestamp(self):
        from amplifier_module_hooks_idd_events import IDDEventRecorder

        recorder = IDDEventRecorder(config={})
        await recorder.handle_event("idd:progress", {"step": "test"})
        entry = recorder._events[0]
        assert "timestamp" in entry
        # ISO format check
        assert "T" in entry["timestamp"]

    @pytest.mark.asyncio
    async def test_event_data_truncated(self):
        from amplifier_module_hooks_idd_events import IDDEventRecorder, _MAX_VALUE_LEN

        recorder = IDDEventRecorder(config={})
        long_value = "x" * 2000
        await recorder.handle_event("idd:test", {"long": long_value})
        stored = recorder._events[0]["data"]["long"]
        assert len(stored) <= _MAX_VALUE_LEN

    @pytest.mark.asyncio
    async def test_event_eviction_on_overflow(self):
        from amplifier_module_hooks_idd_events import IDDEventRecorder

        recorder = IDDEventRecorder(config={"max_events": 5})
        for i in range(10):
            await recorder.handle_event("idd:test", {"i": str(i)})
        assert len(recorder._events) == 5
        # Oldest events evicted; newest kept
        assert recorder._events[0]["data"]["i"] == "5"

    @pytest.mark.asyncio
    async def test_end_to_end_via_hooks(self):
        """Events recorded when emitted through the full hook registry."""
        from amplifier_module_hooks_idd_events import mount

        coord = FakeCoordinator()
        await mount(coord)

        await coord.hooks.emit("idd:intent_parsed", {"goal": "test"})
        event_log = coord.get_capability("idd.event_log")
        assert event_log is not None
        assert len(event_log) == 1
        assert event_log[0]["event"] == "idd:intent_parsed"


# ===================================================================
# GrammarInjectionHook (hooks-idd-grammar-inject)
# ===================================================================


class TestGrammarInjectionMount:
    @pytest.mark.asyncio
    async def test_mount_registers_prompt_submit(self):
        from amplifier_module_hooks_idd_grammar_inject import mount

        coord = FakeCoordinator()
        await mount(coord)
        assert "prompt:submit" in coord.hooks._handlers
        assert len(coord.hooks._handlers["prompt:submit"]) == 1

    @pytest.mark.asyncio
    async def test_mount_at_priority_3(self):
        from amplifier_module_hooks_idd_grammar_inject import mount

        coord = FakeCoordinator()
        await mount(coord)
        entry = coord.hooks._handlers["prompt:submit"][0]
        assert entry["priority"] == 3

    @pytest.mark.asyncio
    async def test_mount_custom_priority(self):
        from amplifier_module_hooks_idd_grammar_inject import mount

        coord = FakeCoordinator()
        await mount(coord, config={"priority": 7})
        entry = coord.hooks._handlers["prompt:submit"][0]
        assert entry["priority"] == 7

    @pytest.mark.asyncio
    async def test_mount_named_handler(self):
        from amplifier_module_hooks_idd_grammar_inject import mount

        coord = FakeCoordinator()
        await mount(coord)
        entry = coord.hooks._handlers["prompt:submit"][0]
        assert entry["name"] == "idd-grammar-inject"

    @pytest.mark.asyncio
    async def test_cleanup_unregisters(self):
        from amplifier_module_hooks_idd_grammar_inject import mount

        coord = FakeCoordinator()
        cleanup = await mount(coord)
        assert len(coord.hooks._handlers["prompt:submit"]) == 1
        cleanup()
        assert len(coord.hooks._handlers["prompt:submit"]) == 0


class TestGrammarInjectionHandler:
    @pytest.mark.asyncio
    async def test_inject_context_when_grammar_state_exists(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        coord = FakeCoordinator()
        coord.register_capability("idd.grammar_state", _grammar_state_with_decomposition())

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {"prompt": "test"})

        assert result.action == "inject_context"
        assert result.ephemeral is True
        assert result.context_injection_role == "system"
        assert result.context_injection is not None
        assert "IDD GRAMMAR STATE" in result.context_injection

    @pytest.mark.asyncio
    async def test_injection_contains_intent(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        coord = FakeCoordinator()
        coord.register_capability("idd.grammar_state", _grammar_state_with_decomposition())

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {})
        assert result.context_injection is not None
        assert "Add caching" in result.context_injection

    @pytest.mark.asyncio
    async def test_injection_contains_criteria_status(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        coord = FakeCoordinator()
        coord.register_capability("idd.grammar_state", _grammar_state_with_decomposition())

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {})
        assert result.context_injection is not None
        assert "[PASS]" in result.context_injection
        assert "[pending]" in result.context_injection

    @pytest.mark.asyncio
    async def test_injection_contains_progress(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        coord = FakeCoordinator()
        coord.register_capability("idd.grammar_state", _grammar_state_with_decomposition())

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {})
        assert result.context_injection is not None
        assert "1/3" in result.context_injection
        assert "executing" in result.context_injection

    @pytest.mark.asyncio
    async def test_continue_when_no_grammar_state(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        coord = FakeCoordinator()
        # No grammar state registered

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {"prompt": "test"})
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_continue_when_no_decomposition(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        coord = FakeCoordinator()
        coord.register_capability("idd.grammar_state", GrammarState())  # no decomposition

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {})
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_injection_includes_corrections(self):
        from amplifier_module_hooks_idd_grammar_inject import GrammarInjectionHook

        gs = _grammar_state_with_decomposition()
        gs.corrections = [
            CorrectionRecord(
                timestamp="now",
                primitive="intent",
                old_value="old",
                new_value="new",
                reason="user clarified the goal",
            )
        ]

        coord = FakeCoordinator()
        coord.register_capability("idd.grammar_state", gs)

        hook = GrammarInjectionHook(coord)
        result = await hook.handle_prompt("prompt:submit", {})
        assert result.context_injection is not None
        assert "Corrections: 1 applied" in result.context_injection
        assert "user clarified the goal" in result.context_injection


# ===================================================================
# IDDReporter (hooks-idd-reporter)
# ===================================================================


class TestIDDReporterMount:
    @pytest.mark.asyncio
    async def test_mount_registers_four_events(self):
        from amplifier_module_hooks_idd_reporter import mount

        coord = FakeCoordinator()
        await mount(coord)

        expected_events = [
            "idd:composition_ready",
            "idd:progress",
            "idd:correction",
            "idd:intent_resolved",
        ]
        for event in expected_events:
            assert event in coord.hooks._handlers, f"Missing handler for {event}"
            assert len(coord.hooks._handlers[event]) == 1

    @pytest.mark.asyncio
    async def test_mount_at_priority_15(self):
        from amplifier_module_hooks_idd_reporter import mount

        coord = FakeCoordinator()
        await mount(coord)
        for handlers in coord.hooks._handlers.values():
            for entry in handlers:
                assert entry["priority"] == 15

    @pytest.mark.asyncio
    async def test_mount_custom_priority(self):
        from amplifier_module_hooks_idd_reporter import mount

        coord = FakeCoordinator()
        await mount(coord, config={"priority": 20})
        for handlers in coord.hooks._handlers.values():
            for entry in handlers:
                assert entry["priority"] == 20

    @pytest.mark.asyncio
    async def test_cleanup_unregisters_all(self):
        from amplifier_module_hooks_idd_reporter import mount

        coord = FakeCoordinator()
        cleanup = await mount(coord)
        total_before = sum(len(h) for h in coord.hooks._handlers.values())
        assert total_before == 4

        cleanup()
        total_after = sum(len(h) for h in coord.hooks._handlers.values())
        assert total_after == 0


class TestIDDReporterCompositionReady:
    @pytest.mark.asyncio
    async def test_returns_user_message_with_plan(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_composition_ready(
            "idd:composition_ready",
            {"plan": "## Intent (WHY)\n  Goal: Add caching"},
        )
        assert result.action == "continue"
        assert result.user_message is not None
        assert "IDD Plan" in result.user_message
        assert "Add caching" in result.user_message

    @pytest.mark.asyncio
    async def test_empty_plan_returns_continue(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_composition_ready("idd:composition_ready", {"plan": ""})
        assert result.action == "continue"
        assert result.user_message is None


class TestIDDReporterProgress:
    @pytest.mark.asyncio
    async def test_returns_step_completion_message(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_progress(
            "idd:progress",
            {"step": "explorer-0", "completed": 2, "total": 5},
        )
        assert result.action == "continue"
        assert result.user_message is not None
        assert "2/5" in result.user_message
        assert "explorer-0" in result.user_message
        assert "completed" in result.user_message

    @pytest.mark.asyncio
    async def test_progress_with_unknown_step(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_progress("idd:progress", {})
        assert result.user_message is not None
        assert "unknown" in result.user_message


class TestIDDReporterCorrection:
    @pytest.mark.asyncio
    async def test_returns_correction_message(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_correction(
            "idd:correction",
            {"primitive": "intent", "reason": "user clarified goal"},
        )
        assert result.action == "continue"
        assert result.user_message is not None
        assert "intent" in result.user_message
        assert "user clarified goal" in result.user_message

    @pytest.mark.asyncio
    async def test_correction_without_reason(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_correction("idd:correction", {"primitive": "trigger"})
        assert result.user_message is not None
        assert "trigger" in result.user_message


class TestIDDReporterResolved:
    @pytest.mark.asyncio
    async def test_completed_status_shows_success(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_resolved(
            "idd:intent_resolved",
            {
                "status": "completed",
                "summary": "All done",
                "success_criteria": [],
            },
        )
        assert result.action == "continue"
        assert result.user_message is not None
        assert "resolved successfully" in result.user_message

    @pytest.mark.asyncio
    async def test_failed_status_shows_failure(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_resolved(
            "idd:intent_resolved",
            {"status": "failed", "summary": "Something broke"},
        )
        assert result.user_message is not None
        assert "failed" in result.user_message

    @pytest.mark.asyncio
    async def test_resolved_includes_summary(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_resolved(
            "idd:intent_resolved",
            {"status": "completed", "summary": "Cache layer deployed"},
        )
        assert result.user_message is not None
        assert "Cache layer deployed" in result.user_message

    @pytest.mark.asyncio
    async def test_resolved_with_criteria(self):
        from amplifier_module_hooks_idd_reporter import IDDReporter

        reporter = IDDReporter()
        result = await reporter.handle_resolved(
            "idd:intent_resolved",
            {
                "status": "completed",
                "summary": "",
                "success_criteria": [
                    {"name": "Response < 200ms", "pass": True},
                    {"name": "Hit ratio > 80%", "pass": False},
                ],
            },
        )
        assert result.user_message is not None
        msg = result.user_message
        assert "Response < 200ms" in msg
        assert "Hit ratio > 80%" in msg


# ===================================================================
# IDDConfirmationGate — correction pipeline (P0-1)
# ===================================================================


class TestIDDConfirmationGateConstructor:
    def test_constructor_accepts_coordinator_and_config(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        coord = FakeCoordinator()
        gate = IDDConfirmationGate(coord, {"timeout": 30, "enabled": True})
        assert gate._timeout == 30.0
        assert gate._enabled is True
        assert gate._coordinator is coord

    def test_constructor_defaults(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        coord = FakeCoordinator()
        gate = IDDConfirmationGate(coord, {})
        assert gate._timeout == 15.0
        assert gate._enabled is True
        assert gate._show_plan is True


class TestIDDConfirmationGateMount:
    @pytest.mark.asyncio
    async def test_mount_registers_two_handlers(self):
        from amplifier_module_hooks_idd_confirmation import mount

        coord = FakeCoordinator()
        await mount(coord, {"timeout": 10})
        assert "idd:composition_ready" in coord.hooks._handlers
        assert "idd:confirmation_response" in coord.hooks._handlers
        assert len(coord.hooks._handlers["idd:composition_ready"]) == 1
        assert len(coord.hooks._handlers["idd:confirmation_response"]) == 1

    @pytest.mark.asyncio
    async def test_cleanup_unregisters(self):
        from amplifier_module_hooks_idd_confirmation import mount

        coord = FakeCoordinator()
        cleanup = await mount(coord)
        cleanup()
        assert len(coord.hooks._handlers.get("idd:composition_ready", [])) == 0
        assert len(coord.hooks._handlers.get("idd:confirmation_response", [])) == 0


class TestIDDConfirmationGateResponse:
    @pytest.mark.asyncio
    async def test_timeout_returns_continue(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        gate = IDDConfirmationGate(FakeCoordinator(), {})
        result = await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": None, "timed_out": True},
        )
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_empty_response_returns_continue(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        gate = IDDConfirmationGate(FakeCoordinator(), {})
        result = await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "", "timed_out": False},
        )
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_pause_returns_deny(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        gate = IDDConfirmationGate(FakeCoordinator(), {})
        result = await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "pause", "timed_out": False},
        )
        assert result.action == "deny"

    @pytest.mark.asyncio
    async def test_continue_returns_continue(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        gate = IDDConfirmationGate(FakeCoordinator(), {})
        result = await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "yes", "timed_out": False},
        )
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_correction_returns_modify(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        gate = IDDConfirmationGate(FakeCoordinator(), {})
        result = await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "Focus on Redis only", "timed_out": False},
        )
        assert result.action == "modify"
        assert result.data["user_correction"] == "Focus on Redis only"

    @pytest.mark.asyncio
    async def test_correction_writes_correction_record_to_grammar_state(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        coord = FakeCoordinator()
        gs = _grammar_state_with_decomposition()
        coord.register_capability("idd.grammar_state", gs)

        gate = IDDConfirmationGate(coord, {})
        await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "Focus on Redis only", "timed_out": False},
        )

        assert len(gs.corrections) == 1
        rec = gs.corrections[0]
        assert rec.primitive == "intent"
        assert rec.old_value == "Add caching"
        assert rec.new_value == "Focus on Redis only"
        assert "Layer 2" in rec.reason

    @pytest.mark.asyncio
    async def test_correction_emits_idd_correction_event(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        coord = FakeCoordinator()
        gs = _grammar_state_with_decomposition()
        coord.register_capability("idd.grammar_state", gs)

        gate = IDDConfirmationGate(coord, {})
        await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "Focus on Redis only", "timed_out": False},
        )

        emitted = [e for e in coord.hooks._emitted if e["event"] == "idd:correction"]
        assert len(emitted) == 1
        assert emitted[0]["data"]["primitive"] == "intent"
        assert "Focus on Redis only" in emitted[0]["data"]["reason"]

    @pytest.mark.asyncio
    async def test_correction_without_grammar_state_still_returns_modify(self):
        """Even if there's no grammar state, the modify action still works."""
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        coord = FakeCoordinator()
        # No grammar state registered

        gate = IDDConfirmationGate(coord, {})
        result = await gate.handle_confirmation_response(
            "idd:confirmation_response",
            {"response": "Change direction", "timed_out": False},
        )
        assert result.action == "modify"

    @pytest.mark.asyncio
    async def test_disabled_gate_returns_continue(self):
        from amplifier_module_hooks_idd_confirmation import IDDConfirmationGate

        gate = IDDConfirmationGate(FakeCoordinator(), {"enabled": False})
        result = await gate.handle_composition_ready(
            "idd:composition_ready",
            {"plan": "some plan"},
        )
        assert result.action == "continue"


# ===================================================================
# IDDEventRecorder — priority fix (P2-2)
# ===================================================================


class TestIDDEventRecorderPriority:
    @pytest.mark.asyncio
    async def test_composition_ready_registered_at_priority_5(self):
        from amplifier_module_hooks_idd_events import mount

        coord = FakeCoordinator()
        await mount(coord)

        handlers = coord.hooks._handlers.get("idd:composition_ready", [])
        assert len(handlers) == 1
        assert handlers[0]["priority"] == 5

    @pytest.mark.asyncio
    async def test_other_events_remain_at_priority_10(self):
        from amplifier_module_hooks_idd_events import mount, _IDD_EVENTS

        coord = FakeCoordinator()
        await mount(coord)

        for event in _IDD_EVENTS:
            if event == "idd:composition_ready":
                continue
            handlers = coord.hooks._handlers.get(event, [])
            assert len(handlers) == 1
            assert handlers[0]["priority"] == 10, f"{event} should be priority 10"


# ===================================================================
# IDDMemoryBridge (hooks-idd-memory-bridge)
# ===================================================================


class TestIDDMemoryBridgeMount:
    """Memory bridge hook registration."""

    @pytest.mark.asyncio
    async def test_mount_registers_two_handlers(self):
        coord = FakeCoordinator()
        cleanup = await memory_bridge_mount(coord, {})
        handlers = coord.hooks._handlers
        assert "idd:intent_resolved" in handlers
        assert "idd:correction" in handlers
        cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_unregisters(self):
        coord = FakeCoordinator()
        cleanup = await memory_bridge_mount(coord, {})
        cleanup()
        assert len(coord.hooks._handlers.get("idd:intent_resolved", [])) == 0
        assert len(coord.hooks._handlers.get("idd:correction", [])) == 0

    @pytest.mark.asyncio
    async def test_mount_at_priority_12(self):
        coord = FakeCoordinator()
        await memory_bridge_mount(coord, {})
        for event in ("idd:intent_resolved", "idd:correction"):
            handlers = coord.hooks._handlers.get(event, [])
            assert len(handlers) == 1
            assert handlers[0]["priority"] == 12


class TestIDDMemoryBridgeIntentResolved:
    """Memory bridge stores resolved intents."""

    @pytest.mark.asyncio
    async def test_stores_memory_when_memory_store_available(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_intent_resolved(
            "idd:intent_resolved",
            {
                "status": "completed",
                "summary": "Built caching layer",
                "success_criteria": [{"name": "p95 < 200ms", "pass": True}],
            },
        )
        assert len(store._stored) == 1
        assert "caching layer" in store._stored[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_noop_when_no_memory_store(self):
        coord = FakeCoordinator()
        bridge = IDDMemoryBridge(coord, {})
        # Should not raise
        result = await bridge.handle_intent_resolved(
            "idd:intent_resolved",
            {
                "status": "completed",
                "summary": "test",
            },
        )
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_noop_when_disabled(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {"enabled": False})
        await bridge.handle_intent_resolved(
            "idd:intent_resolved", {"status": "completed", "summary": "test"}
        )
        assert len(store._stored) == 0

    @pytest.mark.asyncio
    async def test_includes_criteria_in_content(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_intent_resolved(
            "idd:intent_resolved",
            {
                "status": "completed",
                "summary": "test",
                "success_criteria": [
                    {"name": "Tests pass", "pass": True, "evidence": "42 passed"},
                    {"name": "Coverage > 80%", "pass": False},
                ],
            },
        )
        content = store._stored[0]["content"]
        assert "PASS" in content
        assert "FAIL" in content
        assert "Tests pass" in content

    @pytest.mark.asyncio
    async def test_tags_include_status(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_intent_resolved(
            "idd:intent_resolved",
            {
                "status": "completed",
                "summary": "test",
            },
        )
        assert "completed" in store._stored[0]["tags"]
        assert "idd" in store._stored[0]["tags"]
        assert "intent-resolved" in store._stored[0]["tags"]

    @pytest.mark.asyncio
    async def test_importance_higher_for_completed(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_intent_resolved(
            "idd:intent_resolved", {"status": "completed", "summary": "test"}
        )
        assert store._stored[0]["importance"] == 0.8

    @pytest.mark.asyncio
    async def test_importance_lower_for_non_completed(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_intent_resolved(
            "idd:intent_resolved", {"status": "failed", "summary": "test"}
        )
        assert store._stored[0]["importance"] == 0.6


class TestIDDMemoryBridgeCorrection:
    """Memory bridge stores corrections."""

    @pytest.mark.asyncio
    async def test_stores_correction_memory(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_correction(
            "idd:correction",
            {
                "primitive": "intent",
                "reason": "Skip mobile for now",
            },
        )
        assert len(store._stored) == 1
        assert "correction" in store._stored[0]["tags"]
        assert "Skip mobile" in store._stored[0]["content"]

    @pytest.mark.asyncio
    async def test_skips_empty_reason(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_correction(
            "idd:correction",
            {
                "primitive": "intent",
                "reason": "",
            },
        )
        assert len(store._stored) == 0

    @pytest.mark.asyncio
    async def test_correction_tags_include_primitive(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {})
        await bridge.handle_correction(
            "idd:correction",
            {
                "primitive": "trigger",
                "reason": "Change to manual approval",
            },
        )
        assert "trigger" in store._stored[0]["tags"]

    @pytest.mark.asyncio
    async def test_correction_noop_when_no_memory_store(self):
        coord = FakeCoordinator()
        bridge = IDDMemoryBridge(coord, {})
        result = await bridge.handle_correction(
            "idd:correction",
            {
                "primitive": "intent",
                "reason": "test",
            },
        )
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_correction_noop_when_disabled(self):
        store = FakeMemoryStore()
        coord = FakeCoordinator()
        coord.register_capability("memory.store", store)
        bridge = IDDMemoryBridge(coord, {"enabled": False})
        await bridge.handle_correction(
            "idd:correction",
            {
                "primitive": "intent",
                "reason": "test",
            },
        )
        assert len(store._stored) == 0
