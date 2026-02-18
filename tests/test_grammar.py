"""Tests for the IDD Grammar data models."""

from __future__ import annotations

import json

from amplifier_module_tool_idd.grammar import (
    AgentAssignment,
    BehaviorReference,
    ContextRequirement,
    CorrectionRecord,
    Decomposition,
    GrammarState,
    IntentPrimitive,
    SuccessCriterionStatus,
    TriggerPrimitive,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_decomposition(**overrides) -> Decomposition:
    """Build a minimal valid Decomposition with optional overrides."""
    defaults = {
        "intent": IntentPrimitive(goal="test goal", success_criteria=["it works"]),
        "trigger": TriggerPrimitive(activation="user request"),
        "agents": [AgentAssignment(name="self", role="exec", instruction="do it")],
        "context": ContextRequirement(),
        "behaviors": [],
    }
    defaults.update(overrides)
    return Decomposition(**defaults)


def _full_decomposition() -> Decomposition:
    """Build a fully-populated Decomposition."""
    return Decomposition(
        intent=IntentPrimitive(
            goal="Add caching to the API",
            success_criteria=["Response < 200ms", "Hit ratio > 80%"],
            scope_in=["API endpoints", "Redis"],
            scope_out=["DB schema"],
            values=["performance", "simplicity"],
        ),
        trigger=TriggerPrimitive(
            activation="user request",
            pre_conditions=["Redis reachable"],
            confirmation="human",
        ),
        agents=[
            AgentAssignment(name="explorer", role="investigator", instruction="map API"),
            AgentAssignment(name="builder", role="implementer", instruction="build cache"),
        ],
        context=ContextRequirement(
            auto_detected=["Python project"],
            provided=["Redis URL"],
            to_discover=["Current latency"],
        ),
        behaviors=[BehaviorReference(name="tdd"), BehaviorReference(name="incremental")],
        raw_input="Add caching to the API",
        confidence=0.85,
    )


# ===================================================================
# Primitive creation with defaults
# ===================================================================


class TestPrimitiveDefaults:
    """Verify all dataclass instances can be created with their defaults."""

    def test_intent_primitive_required_only(self):
        intent = IntentPrimitive(goal="do stuff", success_criteria=["done"])
        assert intent.goal == "do stuff"
        assert intent.success_criteria == ["done"]
        assert intent.scope_in == []
        assert intent.scope_out == []
        assert intent.values == []

    def test_trigger_primitive_defaults(self):
        trigger = TriggerPrimitive(activation="manual")
        assert trigger.activation == "manual"
        assert trigger.pre_conditions == []
        assert trigger.confirmation == "auto"

    def test_agent_assignment(self):
        agent = AgentAssignment(name="explorer", role="scout", instruction="look around")
        assert agent.name == "explorer"
        assert agent.role == "scout"
        assert agent.instruction == "look around"

    def test_context_requirement_all_defaults(self):
        ctx = ContextRequirement()
        assert ctx.auto_detected == []
        assert ctx.provided == []
        assert ctx.to_discover == []

    def test_behavior_reference(self):
        beh = BehaviorReference(name="tdd")
        assert beh.name == "tdd"


# ===================================================================
# Decomposition
# ===================================================================


class TestDecomposition:
    """Verify Decomposition creation, serialisation, and edge cases."""

    def test_empty_decomposition_minimal(self):
        """Minimal valid state: required fields only, empty collections."""
        d = _minimal_decomposition()
        assert d.raw_input == ""
        assert d.confidence == 0.0
        assert d.behaviors == []
        assert d.context.auto_detected == []

    def test_full_decomposition_all_fields(self):
        """All five primitives fully populated."""
        d = _full_decomposition()
        assert d.intent.goal == "Add caching to the API"
        assert len(d.intent.success_criteria) == 2
        assert len(d.agents) == 2
        assert len(d.behaviors) == 2
        assert d.confidence == 0.85
        assert d.raw_input == "Add caching to the API"

    def test_to_dict_returns_plain_dict(self):
        d = _minimal_decomposition()
        result = d.to_dict()
        assert isinstance(result, dict)
        assert "intent" in result
        assert "trigger" in result
        assert "agents" in result
        assert "context" in result
        assert "behaviors" in result

    def test_to_dict_is_json_safe(self):
        """to_dict() should produce a structure json.dumps can handle."""
        d = _full_decomposition()
        serialised = json.dumps(d.to_dict())
        roundtrip = json.loads(serialised)
        assert roundtrip["intent"]["goal"] == "Add caching to the API"
        assert roundtrip["confidence"] == 0.85

    def test_to_json_returns_valid_json_string(self):
        d = _full_decomposition()
        json_str = d.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["intent"]["goal"] == "Add caching to the API"

    def test_to_json_compact_format(self):
        """to_json() uses compact separators (no spaces after : and ,)."""
        d = _minimal_decomposition()
        json_str = d.to_json()
        # Compact JSON has no spaces after colons or commas
        assert ": " not in json_str or ", " not in json_str


# ===================================================================
# CorrectionRecord
# ===================================================================


class TestCorrectionRecord:
    def test_creation(self):
        rec = CorrectionRecord(
            timestamp="2025-01-01T00:00:00Z",
            primitive="intent",
            old_value="old goal",
            new_value="new goal",
            reason="user clarified",
        )
        assert rec.primitive == "intent"
        assert rec.reason == "user clarified"

    def test_serialises_via_asdict(self):
        from dataclasses import asdict

        rec = CorrectionRecord(
            timestamp="2025-01-01T00:00:00Z",
            primitive="trigger",
            old_value="auto",
            new_value="human",
            reason="destructive action",
        )
        d = asdict(rec)
        assert d["primitive"] == "trigger"
        assert d["old_value"] == "auto"
        assert d["new_value"] == "human"


# ===================================================================
# SuccessCriterionStatus
# ===================================================================


class TestSuccessCriterionStatus:
    def test_default_none_state(self):
        """Default passed=None means 'not yet evaluated'."""
        scs = SuccessCriterionStatus(name="Response < 200ms")
        assert scs.name == "Response < 200ms"
        assert scs.passed is None
        assert scs.evidence == ""

    def test_passed_true(self):
        scs = SuccessCriterionStatus(name="Criterion A", passed=True, evidence="measured 150ms")
        assert scs.passed is True
        assert scs.evidence == "measured 150ms"

    def test_passed_false(self):
        scs = SuccessCriterionStatus(name="Criterion B", passed=False, evidence="measured 500ms")
        assert scs.passed is False

    def test_all_three_states(self):
        """None, True, False are the only three meaningful states."""
        states = [
            SuccessCriterionStatus(name="a"),
            SuccessCriterionStatus(name="b", passed=True),
            SuccessCriterionStatus(name="c", passed=False),
        ]
        assert states[0].passed is None
        assert states[1].passed is True
        assert states[2].passed is False


# ===================================================================
# GrammarState
# ===================================================================


class TestGrammarState:
    def test_default_state(self):
        gs = GrammarState()
        assert gs.decomposition is None
        assert gs.corrections == []
        assert gs.criteria_status == []
        assert gs.steps_completed == 0
        assert gs.steps_total == 0
        assert gs.status == "pending"

    def test_to_dict(self):
        gs = GrammarState()
        d = gs.to_dict()
        assert isinstance(d, dict)
        assert d["status"] == "pending"
        assert d["decomposition"] is None
        assert d["steps_completed"] == 0

    def test_to_json_returns_valid_json(self):
        gs = GrammarState(decomposition=_minimal_decomposition())
        json_str = gs.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["status"] == "pending"
        assert parsed["decomposition"]["intent"]["goal"] == "test goal"

    def test_to_json_pretty_printed(self):
        """GrammarState.to_json() uses indent=2 (human-readable)."""
        gs = GrammarState()
        json_str = gs.to_json()
        assert "\n" in json_str  # indented output has newlines

    def test_summary_no_decomposition(self):
        gs = GrammarState()
        summary = gs.summary()
        assert "[IDD] No decomposition yet." in summary

    def test_summary_has_all_five_primitives(self):
        """summary() must render all five primitive sections."""
        gs = GrammarState(decomposition=_full_decomposition())
        summary = gs.summary()
        assert "## Intent (WHY)" in summary
        assert "## Trigger (WHEN)" in summary
        assert "## Agents (WHO)" in summary
        assert "## Context (WHAT)" in summary
        assert "## Behaviors (HOW)" in summary
        assert "## Progress" in summary

    def test_summary_includes_goal_and_agents(self):
        gs = GrammarState(decomposition=_full_decomposition())
        summary = gs.summary()
        assert "Add caching to the API" in summary
        assert "explorer" in summary
        assert "builder" in summary

    def test_summary_shows_progress(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(),
            status="executing",
            steps_completed=2,
            steps_total=5,
        )
        summary = gs.summary()
        assert "Status: executing" in summary
        assert "2/5" in summary

    def test_summary_shows_corrections_count(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(),
            corrections=[
                CorrectionRecord(
                    timestamp="now",
                    primitive="intent",
                    old_value="a",
                    new_value="b",
                    reason="c",
                )
            ],
        )
        summary = gs.summary()
        assert "Corrections: 1" in summary

    def test_criterion_marker_passed(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(),
            criteria_status=[SuccessCriterionStatus(name="it works", passed=True)],
        )
        assert gs._criterion_marker("it works") == "[x]"

    def test_criterion_marker_failed(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(),
            criteria_status=[SuccessCriterionStatus(name="it works", passed=False)],
        )
        assert gs._criterion_marker("it works") == "[ ]"

    def test_criterion_marker_pending(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(),
            criteria_status=[SuccessCriterionStatus(name="it works", passed=None)],
        )
        assert gs._criterion_marker("it works") == "[?]"

    def test_criterion_marker_unknown(self):
        """Criterion not tracked at all returns [-]."""
        gs = GrammarState(decomposition=_minimal_decomposition())
        assert gs._criterion_marker("missing criterion") == "[-]"

    def test_summary_behaviors_default_when_empty(self):
        gs = GrammarState(decomposition=_minimal_decomposition(behaviors=[]))
        summary = gs.summary()
        assert "(default)" in summary

    def test_summary_behaviors_listed(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(
                behaviors=[BehaviorReference(name="tdd"), BehaviorReference(name="incremental")]
            )
        )
        summary = gs.summary()
        assert "tdd" in summary
        assert "incremental" in summary

    def test_summary_scope_in_out(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(
                intent=IntentPrimitive(
                    goal="g",
                    success_criteria=["ok"],
                    scope_in=["API"],
                    scope_out=["DB"],
                )
            )
        )
        summary = gs.summary()
        assert "In scope:" in summary
        assert "API" in summary
        assert "Out scope:" in summary
        assert "DB" in summary

    def test_summary_trigger_details(self):
        gs = GrammarState(
            decomposition=_minimal_decomposition(
                trigger=TriggerPrimitive(
                    activation="cron job",
                    pre_conditions=["Redis up"],
                    confirmation="human",
                )
            )
        )
        summary = gs.summary()
        assert "cron job" in summary
        assert "Redis up" in summary
        assert "Confirmation: human" in summary
