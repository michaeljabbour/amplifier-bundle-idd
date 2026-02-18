"""IDD Orchestrator — Intent-Driven Design orchestration module for Amplifier.

Wraps an inner orchestrator with Layer 1→2 decomposition (natural language
to five IDD primitives) and Layer 2→1 reporting (structured progress back
to the human).

Module entry point
------------------
``mount(coordinator, config)`` registers the :class:`IDDOrchestrator` as
the session's orchestrator.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from .compiler import IDDCompiler
from .grammar import GrammarState, SuccessCriterionStatus
from .parser import IDDParser

# Conditional import — amplifier_core may not be present during unit tests.
try:
    from amplifier_core.models import ChatMessage, ChatRequest  # pyright: ignore[reportAttributeAccessIssue]
except ImportError:  # pragma: no cover
    ChatRequest = None  # type: ignore[assignment,misc]
    ChatMessage = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

__amplifier_module_type__ = "orchestrator"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class IDDOrchestrator:
    """IDD orchestrator that wraps an inner orchestrator.

    Handles Layer 1→2 decomposition and Layer 2→1 reporting, delegating
    actual LLM execution to agent spawning or direct provider calls.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._parser = IDDParser()
        self._compiler = IDDCompiler()
        self._grammar_state = GrammarState()

    # -- Orchestrator protocol ------------------------------------------------

    async def execute(
        self,
        prompt: str,
        context: Any,
        providers: dict[str, Any],
        tools: dict[str, Any],
        hooks: Any,
        **kwargs: Any,
    ) -> str:
        """Execute the full IDD lifecycle for a single user prompt.

        Parameters
        ----------
        prompt:
            Raw natural-language input from the user (Layer 1).
        context:
            The session's :class:`ContextManager`.
        providers:
            Mapping of provider name → provider instance.
        tools:
            Mapping of tool name → tool instance.
        hooks:
            The session's :class:`HookRegistry`.
        **kwargs:
            Must include ``coordinator`` (the session coordinator).

        Returns
        -------
        str
            Human-readable completion summary (Layer 2→1).
        """
        coordinator = kwargs.get("coordinator")

        # 1. Register grammar state as a capability ----------------------------
        if coordinator:
            coordinator.register_capability("idd.grammar_state", self._grammar_state)

        # 2. Discover available agents -----------------------------------------
        available_agents: list[str] = []
        if coordinator:
            available_agents = list(coordinator.config.get("agents", {}).keys())

        # 3. Parse: Layer 1 → Layer 2 -----------------------------------------
        try:
            decomposition = await self._parser.parse(prompt, providers, available_agents)
        except Exception:
            logger.exception("IDD parse failed — using fallback decomposition")
            decomposition = self._parser._fallback_decomposition(prompt, reason="parse exception")

        self._grammar_state.decomposition = decomposition
        self._grammar_state.criteria_status = [
            SuccessCriterionStatus(name=c) for c in decomposition.intent.success_criteria
        ]

        # 4. Emit idd:intent_parsed -------------------------------------------
        await _emit_safe(
            hooks,
            "idd:intent_parsed",
            {
                "decomposition": decomposition.to_dict(),
                "raw_input": prompt,
            },
        )

        # 5. Present plan and open timed confirmation gate ---------------------
        #
        # The ``idd:composition_ready`` event is intercepted by the
        # ``hooks-idd-confirmation`` module which opens a NON-BLOCKING
        # timed window (default 15 s, configurable).  Three outcomes:
        #
        #   * Timeout / no reply -> ``action="continue"`` (default-allow)
        #   * User provides direction -> ``action="modify"`` with correction
        #   * User says "pause"/"stop" -> ``action="deny"``
        #
        plan_summary = self._grammar_state.summary()
        gate_result = await _emit_safe(
            hooks,
            "idd:composition_ready",
            {
                "plan": plan_summary,
                "decomposition": decomposition.to_dict(),
            },
        )

        # 6. Process confirmation gate outcome ---------------------------------
        gate_result = await self._process_confirmation(gate_result, hooks, decomposition)
        if gate_result == "cancelled":
            return "[IDD] Execution paused by user. Provide new direction when ready."

        # 7. Compile to executable recipe --------------------------------------
        recipe = self._compiler.compile(decomposition)
        self._grammar_state.steps_total = len(recipe.get("steps", []))
        self._grammar_state.status = "executing"

        # 8. Execute steps sequentially (respecting depends_on) ----------------
        results: list[dict[str, str]] = []
        steps = recipe.get("steps", [])
        for i, step in enumerate(steps):
            try:
                step_result = await self._execute_step(
                    step, context, providers, tools, hooks, coordinator, results
                )
            except Exception as exc:
                logger.exception("IDD step %s failed", step.get("name"))
                step_result = f"[Error in step {step.get('name', i)}]: {exc}"

            results.append({"name": step["name"], "result": step_result})
            self._grammar_state.steps_completed = i + 1

            # Emit progress
            await _emit_safe(
                hooks,
                "idd:progress",
                {
                    "step": step["name"],
                    "completed": i + 1,
                    "total": self._grammar_state.steps_total,
                    "criteria_status": [asdict(c) for c in self._grammar_state.criteria_status],
                },
            )

        # 9. Mark completed ----------------------------------------------------
        self._grammar_state.status = "completed"

        # 10. Emit idd:intent_resolved ----------------------------------------
        await _emit_safe(
            hooks,
            "idd:intent_resolved",
            self._build_resolved_payload(results),
        )

        # 11. Return human-readable summary (str per protocol) -----------------
        return self._build_completion_summary(results)

    # -- Confirmation gate ----------------------------------------------------

    async def _process_confirmation(
        self,
        gate_result: Any,
        hooks: Any,
        decomposition: Any,
    ) -> str:
        """Process the Layer 2 confirmation gate outcome.

        The ``idd:composition_ready`` event is handled by the
        ``hooks-idd-confirmation`` module which opens a timed,
        non-blocking window (default 15 s).  This method interprets
        the hook result:

        * ``action="continue"`` (or timeout) -- proceed as planned.
        * ``action="modify"`` with ``data.user_correction`` -- apply
          the correction to Grammar state and re-parse if needed.
        * ``action="deny"`` -- user said "pause"; halt execution.

        Returns
        -------
        str
            ``"ok"`` to proceed, ``"cancelled"`` to halt.
        """
        if gate_result is None:
            return "ok"

        action = getattr(gate_result, "action", "continue")

        if action == "deny":
            self._grammar_state.status = "cancelled"
            return "cancelled"

        if action == "modify":
            data = getattr(gate_result, "data", None) or {}
            correction_text = data.get("user_correction", "")
            if correction_text:
                await self._apply_user_correction(correction_text, hooks, decomposition)

        return "ok"

    async def _apply_user_correction(
        self,
        correction_text: str,
        hooks: Any,
        decomposition: Any,
    ) -> None:
        """Apply a user's mid-flight correction to the Grammar state.

        Records the correction and emits ``idd:correction`` so that
        telemetry and the reporter can track the change.
        """
        from datetime import datetime, timezone
        from .grammar import CorrectionRecord

        record = CorrectionRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            primitive="user-directed",
            old_value="(original plan)",
            new_value=correction_text[:500],
            reason=f"User correction at Layer 2 confirmation: {correction_text[:200]}",
        )
        self._grammar_state.corrections.append(record)

        await _emit_safe(
            hooks,
            "idd:correction",
            {
                "primitive": record.primitive,
                "old_value": record.old_value,
                "new_value": record.new_value,
                "reason": record.reason,
            },
        )

    # -- Step execution -------------------------------------------------------

    async def _execute_step(
        self,
        step: dict[str, Any],
        context: Any,
        providers: dict[str, Any],
        tools: dict[str, Any],
        hooks: Any,
        coordinator: Any,
        prior_results: list[dict[str, str]],
    ) -> str:
        """Execute a single recipe step.

        If the coordinator exposes ``session.spawn``, delegate to a named
        agent.  Otherwise, fall back to a direct LLM call.
        """
        spawn_fn = coordinator.get_capability("session.spawn") if coordinator else None

        if spawn_fn and step.get("agent"):
            instruction = self._build_step_instruction(step, prior_results)
            try:
                result = await spawn_fn(
                    agent_name=step["agent"],
                    instruction=instruction,
                    parent_session=coordinator.session,
                    agent_configs=coordinator.config.get("agents", {}),
                )
                if isinstance(result, dict):
                    return result.get("output", str(result))
                return str(result)
            except Exception:
                logger.warning(
                    "Agent spawn failed for %s — falling back to LLM",
                    step.get("agent"),
                    exc_info=True,
                )
                return await self._execute_with_llm(step, context, providers, tools, hooks)
        else:
            return await self._execute_with_llm(step, context, providers, tools, hooks)

    async def _execute_with_llm(
        self,
        step: dict[str, Any],
        context: Any,
        providers: dict[str, Any],
        tools: dict[str, Any],
        hooks: Any,
    ) -> str:
        """Execute a step with a direct LLM call (fallback path)."""
        if ChatRequest is None or ChatMessage is None:
            return "[Error: amplifier_core not available for LLM fallback]"

        provider = next(iter(providers.values()), None) if providers else None
        if not provider:
            return "[Error: No provider available]"

        step_name = step.get("name", "unknown")
        instruction = step.get("instruction", "")

        request = ChatRequest(
            model="",
            messages=[
                ChatMessage(
                    role="system",
                    content=f"You are executing step: {step_name}",
                ),
                ChatMessage(role="user", content=instruction),
            ],
        )

        try:
            response = await provider.complete(request)
            return response.content or ""
        except Exception as exc:
            logger.exception("LLM call failed for step %s", step_name)
            return f"[Error: LLM call failed for {step_name}: {exc}]"

    # -- Instruction building -------------------------------------------------

    def _build_step_instruction(
        self,
        step: dict[str, Any],
        prior_results: list[dict[str, str]],
    ) -> str:
        """Build an instruction with IDD grammar state for agent delegation.

        Includes the current grammar state, prior step results resolved
        through template references, and the step's own instruction.
        """
        parts: list[str] = [
            "[IDD GRAMMAR STATE]",
            self._grammar_state.to_json(),
            "",
            "[YOUR TASK]",
            step.get("instruction", ""),
        ]

        includes = step.get("context", {}).get("include", [])
        if includes and prior_results:
            parts.append("")
            parts.append("[PRIOR CONTEXT]")
            for ref in includes:
                resolved = ref
                for pr in prior_results:
                    template = f"{{{{steps.{pr['name']}.result}}}}"
                    # Truncate long results to keep prompts manageable
                    resolved = resolved.replace(template, pr["result"][:2000])
                parts.append(resolved)

        return "\n".join(parts)

    # -- Payload builders -----------------------------------------------------

    def _build_resolved_payload(self, results: list[dict[str, str]]) -> dict[str, Any]:
        """Build the ``idd:intent_resolved`` event payload."""
        return {
            "status": self._grammar_state.status,
            "steps_completed": self._grammar_state.steps_completed,
            "steps_total": self._grammar_state.steps_total,
            "criteria_status": [asdict(c) for c in self._grammar_state.criteria_status],
            "corrections": [asdict(c) for c in self._grammar_state.corrections],
            "results": results,
            "summary": self._grammar_state.summary(),
        }

    def _build_completion_summary(self, results: list[dict[str, str]]) -> str:
        """Build a human-readable completion summary returned to the user."""
        lines: list[str] = [
            "[IDD Execution Complete]",
            "",
            self._grammar_state.summary(),
            "",
            "## Step Results",
        ]

        for r in results:
            # Show first 500 chars of each result
            preview = r["result"][:500]
            if len(r["result"]) > 500:
                preview += "..."
            lines.append(f"  {r['name']}: {preview}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module mount point
# ---------------------------------------------------------------------------


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:
    """Amplifier module entry point.

    Instantiates the :class:`IDDOrchestrator` and registers it as the
    session's orchestrator via the coordinator.
    """
    config = config or {}
    orchestrator = IDDOrchestrator(config)
    await coordinator.mount("orchestrator", orchestrator)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _emit_safe(hooks: Any, event: str, data: dict[str, Any]) -> Any:
    """Emit a hook event, swallowing errors so execution never crashes."""
    try:
        return await hooks.emit(event, data)
    except Exception:
        logger.warning("Failed to emit %s event", event, exc_info=True)
        return None


def _is_denied(hook_result: Any) -> bool:
    """Check whether a :class:`HookResult` signals denial."""
    if hook_result is None:
        return False
    action = getattr(hook_result, "action", None)
    return action == "deny"
