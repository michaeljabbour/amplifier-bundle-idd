"""IDD Grammar — Core data models for the five IDD primitives.

Defines the compositional grammar that decomposes every agentic interaction
into five orthogonal primitives: Intent (WHY), Trigger (WHEN), Agent (WHO),
Context (WHAT), and Behavior (HOW).

All models use stdlib dataclasses to avoid coupling to amplifier-core.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


# ---------------------------------------------------------------------------
# Primitive data models
# ---------------------------------------------------------------------------


@dataclass
class IntentPrimitive:
    """WHY — the goal, success criteria, and scope boundaries."""

    goal: str
    success_criteria: list[str]
    scope_in: list[str] = field(default_factory=list)
    scope_out: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)


@dataclass
class TriggerPrimitive:
    """WHEN — activation condition and confirmation mode."""

    activation: str
    pre_conditions: list[str] = field(default_factory=list)
    confirmation: str = "auto"  # "auto" | "human" | "none"


@dataclass
class AgentAssignment:
    """WHO — a named agent with a role and instruction."""

    name: str
    role: str
    instruction: str


@dataclass
class ContextRequirement:
    """WHAT — context the task needs, split by discovery status."""

    auto_detected: list[str] = field(default_factory=list)
    provided: list[str] = field(default_factory=list)
    to_discover: list[str] = field(default_factory=list)


@dataclass
class BehaviorReference:
    """HOW — a named behavior to apply during execution."""

    name: str


# ---------------------------------------------------------------------------
# Composite models
# ---------------------------------------------------------------------------


@dataclass
class Decomposition:
    """Full five-primitive decomposition of a user prompt."""

    intent: IntentPrimitive
    trigger: TriggerPrimitive
    agents: list[AgentAssignment]
    context: ContextRequirement
    behaviors: list[BehaviorReference]
    raw_input: str = ""
    confidence: float = 0.0

    # -- serialisation helpers ------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dict (JSON-safe)."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialise to a compact JSON string."""
        return json.dumps(self.to_dict(), separators=(",", ":"))


# ---------------------------------------------------------------------------
# Execution-tracking models
# ---------------------------------------------------------------------------


@dataclass
class CorrectionRecord:
    """Records a mid-flight correction to one of the five primitives."""

    timestamp: str
    primitive: str  # which primitive changed
    old_value: str
    new_value: str
    reason: str


@dataclass
class SuccessCriterionStatus:
    """Tracks evaluation of a single success criterion."""

    name: str
    passed: bool | None = None  # None → not yet evaluated
    evidence: str = ""


@dataclass
class GrammarState:
    """Mutable state that travels with an IDD execution.

    Registered as the ``idd.grammar_state`` capability so hooks,
    behaviors, and reporters can observe and modify the grammar.
    """

    decomposition: Decomposition | None = None
    corrections: list[CorrectionRecord] = field(default_factory=list)
    criteria_status: list[SuccessCriterionStatus] = field(default_factory=list)
    steps_completed: int = 0
    steps_total: int = 0
    status: str = "pending"  # pending | executing | completed | failed | cancelled

    # -- serialisation --------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dict using :func:`dataclasses.asdict`."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    # -- human-readable reporting ---------------------------------------------

    def summary(self) -> str:
        """Produce a human-readable summary for Layer 2→1 reporting.

        Renders all five primitives plus execution progress so a human
        (or an outer orchestrator) can understand what IDD is doing.
        """
        lines: list[str] = []

        if self.decomposition is None:
            lines.append("[IDD] No decomposition yet.")
            return "\n".join(lines)

        d = self.decomposition

        # -- Intent -----------------------------------------------------------
        lines.append("## Intent (WHY)")
        lines.append(f"  Goal: {d.intent.goal}")
        if d.intent.success_criteria:
            lines.append("  Success criteria:")
            for sc in d.intent.success_criteria:
                # Show status if we're tracking it
                marker = self._criterion_marker(sc)
                lines.append(f"    {marker} {sc}")
        if d.intent.scope_in:
            lines.append(f"  In scope:  {', '.join(d.intent.scope_in)}")
        if d.intent.scope_out:
            lines.append(f"  Out scope: {', '.join(d.intent.scope_out)}")
        if d.intent.values:
            lines.append(f"  Values:    {', '.join(d.intent.values)}")

        # -- Trigger ----------------------------------------------------------
        lines.append("")
        lines.append("## Trigger (WHEN)")
        lines.append(f"  Activation:   {d.trigger.activation}")
        if d.trigger.pre_conditions:
            lines.append(f"  Pre-conditions: {', '.join(d.trigger.pre_conditions)}")
        lines.append(f"  Confirmation: {d.trigger.confirmation}")

        # -- Agents -----------------------------------------------------------
        lines.append("")
        lines.append("## Agents (WHO)")
        if d.agents:
            for ag in d.agents:
                lines.append(f"  - {ag.name} ({ag.role})")
                lines.append(f"    {ag.instruction}")
        else:
            lines.append("  (none assigned)")

        # -- Context ----------------------------------------------------------
        lines.append("")
        lines.append("## Context (WHAT)")
        if d.context.auto_detected:
            lines.append(f"  Auto-detected: {', '.join(d.context.auto_detected)}")
        if d.context.provided:
            lines.append(f"  Provided:      {', '.join(d.context.provided)}")
        if d.context.to_discover:
            lines.append(f"  To discover:   {', '.join(d.context.to_discover)}")

        # -- Behaviors --------------------------------------------------------
        lines.append("")
        lines.append("## Behaviors (HOW)")
        if d.behaviors:
            lines.append(f"  {', '.join(b.name for b in d.behaviors)}")
        else:
            lines.append("  (default)")

        # -- Progress ---------------------------------------------------------
        lines.append("")
        lines.append("## Progress")
        lines.append(f"  Status: {self.status}")
        lines.append(f"  Steps:  {self.steps_completed}/{self.steps_total}")
        lines.append(f"  Confidence: {d.confidence:.0%}")

        if self.corrections:
            lines.append(f"  Corrections: {len(self.corrections)}")

        return "\n".join(lines)

    # -- internals ------------------------------------------------------------

    def _criterion_marker(self, criterion_name: str) -> str:
        """Return a status marker for a criterion: [x], [ ], or [?]."""
        for cs in self.criteria_status:
            if cs.name == criterion_name:
                if cs.passed is True:
                    return "[x]"
                if cs.passed is False:
                    return "[ ]"
                return "[?]"
        return "[-]"
