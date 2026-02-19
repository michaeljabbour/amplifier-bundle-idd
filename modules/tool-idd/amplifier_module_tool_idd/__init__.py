"""IDD Tools -- decompose and compile for Intent-Driven Design.

Provides two tools that the LLM calls through the standard orchestrator loop:

``idd_decompose``
    Takes natural language input and decomposes it into five IDD primitives
    (Agent, Context, Behavior, Intent, Trigger) using an LLM call.  Returns
    the structured decomposition as JSON.  Registers the Grammar state as
    the ``idd.grammar_state`` capability so hooks can observe it.

``idd_compile``
    Takes a decomposition (or the current Grammar state) and compiles it
    into executable Amplifier recipe YAML (schema v1.7.0).

No custom orchestrator required -- the standard ``loop-streaming``
orchestrator drives the session.  The LLM decides when to decompose
based on context instructions.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .compiler import IDDCompiler
from .grammar import GrammarState, SuccessCriterionStatus
from .parser import IDDParser

# Conditional import — ToolResult comes from amplifier-core,
# but we guard the import so the module can be tested in isolation.
try:
    from amplifier_core.models import ToolResult, HookResult  # pyright: ignore[reportAttributeAccessIssue]
except ImportError:  # pragma: no cover
    ToolResult = None  # type: ignore[assignment,misc]
    HookResult = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

__amplifier_module_type__ = "tool"


# ---------------------------------------------------------------------------
# Tool: idd_decompose
# ---------------------------------------------------------------------------


class IDDDecomposeTool:
    """Decompose natural language into five IDD primitives.

    The LLM calls this tool when it recognises a task that should be
    structured using Intent-Driven Design.  The tool calls a provider
    internally to parse the input, then returns the structured
    decomposition and registers the Grammar state as a capability.
    """

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator
        self._parser = IDDParser()
        self._grammar_state = GrammarState()

    @property
    def name(self) -> str:
        return "idd_decompose"

    @property
    def description(self) -> str:
        return (
            "Decompose a natural-language task into the five IDD primitives "
            "(Agent/WHO, Context/WHAT, Behavior/HOW, Intent/WHY, Trigger/WHEN). "
            "Returns a structured decomposition with all five primitives filled, "
            "success criteria, and a confidence score. "
            "Use this whenever a task should be broken down before execution."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "The natural language task or goal to decompose.",
                },
            },
            "required": ["input"],
        }

    async def execute(self, input: dict[str, Any]) -> Any:
        """Execute the decomposition."""
        raw_input = input.get("input", "")
        if not raw_input:
            return _tool_result(
                False,
                "No input provided. Pass a natural language task description.",
            )

        # Get available agents and providers from coordinator
        available_agents: list[str] = []
        providers: dict[str, Any] = {}
        try:
            available_agents = list(self._coordinator.config.get("agents", {}).keys())
            providers = self._coordinator.get("providers") or {}
        except Exception:
            logger.debug("Could not read coordinator config", exc_info=True)

        # Parse the input into five primitives
        try:
            decomposition = await self._parser.parse(raw_input, providers, available_agents)
        except Exception:
            logger.exception("IDD decomposition failed")
            decomposition = self._parser._fallback_decomposition(
                raw_input, reason="parse exception"
            )

        # Update grammar state
        self._grammar_state.decomposition = decomposition
        self._grammar_state.criteria_status = [
            SuccessCriterionStatus(name=c) for c in decomposition.intent.success_criteria
        ]
        self._grammar_state.status = "decomposed"
        self._grammar_state.steps_total = len(decomposition.agents)

        # Register as capability so hooks can see it
        try:
            self._coordinator.register_capability("idd.grammar_state", self._grammar_state)
        except Exception:
            logger.debug("Could not register grammar state capability", exc_info=True)

        # Emit idd:intent_parsed event
        try:
            await self._coordinator.hooks.emit(
                "idd:intent_parsed",
                {
                    "decomposition": decomposition.to_dict(),
                    "raw_input": raw_input,
                },
            )
        except Exception:
            logger.debug("Could not emit idd:intent_parsed", exc_info=True)

        # Emit idd:composition_ready — triggers the confirmation gate
        # (15s timeout, default-allow) and the reporter plan display.
        try:
            plan = _build_plan_summary(decomposition)
            await self._coordinator.hooks.emit(
                "idd:composition_ready",
                {
                    "plan": plan,
                    "decomposition": decomposition.to_dict(),
                },
            )
        except Exception:
            logger.debug("Could not emit idd:composition_ready", exc_info=True)

        return _tool_result(
            True,
            json.dumps(decomposition.to_dict(), indent=2),
        )


# ---------------------------------------------------------------------------
# Tool: idd_compile
# ---------------------------------------------------------------------------


class IDDCompileTool:
    """Compile an IDD decomposition into Amplifier recipe YAML.

    Takes the current Grammar state (from a prior ``idd_decompose`` call)
    or a decomposition dict passed directly, and produces executable
    recipe YAML matching Amplifier's recipe schema v1.7.0.
    """

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator
        self._compiler = IDDCompiler()

    @property
    def name(self) -> str:
        return "idd_compile"

    @property
    def description(self) -> str:
        return (
            "Compile an IDD decomposition into executable Amplifier recipe YAML. "
            "Uses the Grammar state from a prior idd_decompose call. "
            "Returns the compiled YAML string ready for the recipes tool."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decomposition_json": {
                    "type": "string",
                    "description": (
                        "Optional: a JSON string of the decomposition to compile. "
                        "If omitted, uses the current Grammar state from a prior "
                        "idd_decompose call."
                    ),
                },
            },
            "required": [],
        }

    async def execute(self, input: dict[str, Any]) -> Any:
        """Execute the compilation."""
        # Try to get decomposition from input or Grammar state
        decomposition = None
        decomposition_json = input.get("decomposition_json", "")

        if decomposition_json:
            try:
                from .parser import IDDParser

                decomposition = IDDParser()._dict_to_decomposition(
                    json.loads(decomposition_json), raw_input=""
                )
            except Exception:
                logger.debug("Could not parse decomposition_json", exc_info=True)

        if decomposition is None:
            # Fall back to grammar state capability
            grammar_state = self._coordinator.get_capability("idd.grammar_state")
            if grammar_state and getattr(grammar_state, "decomposition", None):
                decomposition = grammar_state.decomposition

        if decomposition is None:
            return _tool_result(
                False,
                "No decomposition available. Run idd_decompose first.",
            )

        # Compile to YAML
        try:
            yaml_str = self._compiler.compile_to_yaml(decomposition)
        except Exception:
            logger.exception("IDD compilation failed")
            return _tool_result(False, "Failed to compile decomposition to YAML.")

        return _tool_result(True, yaml_str)


# ---------------------------------------------------------------------------
# Module mount point
# ---------------------------------------------------------------------------


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """Amplifier module entry point.

    Registers ``idd_decompose`` and ``idd_compile`` as tools on the
    coordinator.  Also registers callable capabilities for programmatic
    access and a ``tool:post`` hook for progress tracking.
    """
    config = config or {}
    decompose_tool = IDDDecomposeTool(coordinator)
    compile_tool = IDDCompileTool(coordinator)

    await coordinator.mount("tools", decompose_tool, name=decompose_tool.name)
    await coordinator.mount("tools", compile_tool, name=compile_tool.name)

    # -----------------------------------------------------------------
    # Callable capabilities (P1-2, P1-3)
    # -----------------------------------------------------------------

    async def _decompose_capability(input_text: str) -> Any:
        return await decompose_tool.execute({"input": input_text})

    async def _compile_capability(decomposition_json: str = "") -> Any:
        return await compile_tool.execute({"decomposition_json": decomposition_json})

    def _update_criterion(name: str, passed: bool, evidence: str = "") -> None:
        gs = coordinator.get_capability("idd.grammar_state")
        if gs is None:
            return
        for cs in gs.criteria_status:
            if cs.name == name:
                cs.passed = passed
                cs.evidence = evidence
                return

    try:
        coordinator.register_capability("idd.decompose", _decompose_capability)
        coordinator.register_capability("idd.compile", _compile_capability)
        coordinator.register_capability("idd.update_criterion", _update_criterion)
    except Exception:
        logger.debug("Could not register IDD capabilities", exc_info=True)

    # -----------------------------------------------------------------
    # Intent resolution capability (P2-1)
    # -----------------------------------------------------------------

    async def _resolve_intent(status: str = "completed", summary: str = "") -> None:
        gs = coordinator.get_capability("idd.grammar_state")
        if gs is None:
            return
        gs.status = status
        criteria_data: list[dict[str, Any]] = []
        for cs in getattr(gs, "criteria_status", []):
            criteria_data.append(
                {
                    "name": cs.name,
                    "pass": cs.passed,
                    "evidence": getattr(cs, "evidence", ""),
                }
            )
        try:
            await coordinator.hooks.emit(
                "idd:intent_resolved",
                {
                    "status": status,
                    "summary": summary
                    or (gs.decomposition.intent.goal if gs.decomposition else ""),
                    "success_criteria": criteria_data,
                },
            )
        except Exception:
            logger.debug("Could not emit idd:intent_resolved", exc_info=True)

    try:
        coordinator.register_capability("idd.resolve_intent", _resolve_intent)
    except Exception:
        logger.debug("Could not register idd.resolve_intent capability", exc_info=True)

    # -----------------------------------------------------------------
    # Progress tracking — emit idd:progress on tool completions (P0-3)
    # -----------------------------------------------------------------

    async def _handle_tool_post(event: str, data: dict[str, Any]) -> Any:
        try:
            gs = coordinator.get_capability("idd.grammar_state")
            if gs is None or gs.status not in ("decomposed", "executing"):
                if HookResult is not None:
                    return HookResult(action="continue")
                return {"action": "continue"}

            tool_name = data.get("tool_name", "")
            # Don't count IDD's own tools as progress steps
            if tool_name.startswith("idd_"):
                if HookResult is not None:
                    return HookResult(action="continue")
                return {"action": "continue"}

            gs.status = "executing"
            gs.steps_completed += 1

            # Enrich with telemetry snapshot if available
            telemetry = None
            try:
                metrics_cap = coordinator.get_capability("telemetry.metrics")
                if metrics_cap and callable(metrics_cap):
                    telemetry = metrics_cap()
                elif metrics_cap and hasattr(metrics_cap, "snapshot"):
                    telemetry = metrics_cap.snapshot()
            except Exception:
                pass

            progress_data: dict[str, Any] = {
                "step": tool_name,
                "completed": gs.steps_completed,
                "total": gs.steps_total,
            }
            if telemetry:
                progress_data["telemetry"] = telemetry

            await coordinator.hooks.emit(
                "idd:progress",
                progress_data,
            )
        except Exception:
            logger.debug("Could not emit idd:progress", exc_info=True)

        if HookResult is not None:
            return HookResult(action="continue")
        return {"action": "continue"}

    try:
        coordinator.hooks.register(
            "tool:post",
            _handle_tool_post,
            priority=20,
            name="idd-progress-tracker",
        )
    except Exception:
        logger.debug("Could not register idd-progress-tracker", exc_info=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_plan_summary(decomposition: Any) -> str:
    """Build a concise human-readable plan from a Decomposition.

    This is the text the confirmation gate shows the user during the
    15-second approval window.  Keep it short — the user is scanning,
    not studying.
    """
    parts: list[str] = []

    # Goal
    parts.append(f"Goal: {decomposition.intent.goal}")

    # Agents
    if decomposition.agents:
        agent_lines = [f"  - {a.name} ({a.role})" for a in decomposition.agents]
        parts.append("Agents:\n" + "\n".join(agent_lines))

    # Success criteria
    if decomposition.intent.success_criteria:
        criteria_lines = [f"  - {c}" for c in decomposition.intent.success_criteria]
        parts.append("Success criteria:\n" + "\n".join(criteria_lines))

    # Scope boundaries (only if non-empty)
    if decomposition.intent.scope_out:
        parts.append(f"Out of scope: {', '.join(decomposition.intent.scope_out)}")

    # Confirmation mode
    if decomposition.trigger.confirmation == "human":
        parts.append("Confirmation: human approval required")

    # Confidence
    parts.append(f"Confidence: {decomposition.confidence:.0%}")

    return "\n".join(parts)


def _tool_result(success: bool, output: str) -> Any:
    """Build a ToolResult compatible with Amplifier's tool infrastructure.

    Returns a proper ``ToolResult`` when amplifier-core is available,
    falling back to a plain dict for isolated testing.
    """
    if ToolResult is not None:
        if success:
            return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=output, error={"message": output})
    # Fallback for tests running without amplifier-core
    return {"success": success, "output": output}
