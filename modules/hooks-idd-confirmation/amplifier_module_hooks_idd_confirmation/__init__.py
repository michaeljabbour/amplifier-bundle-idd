"""IDD Layer 2 Confirmation Gate.

Non-blocking, timed confirmation hook for IDD compositions.
When the orchestrator emits ``idd:composition_ready``, this hook
presents the Layer 2 plan to the user with a configurable timeout
(default 15 seconds).  The user can:

* **Do nothing** -- execution continues automatically (default-allow).
* **Reply with corrections** -- the response is attached to the hook
  result so the orchestrator can apply a mid-flight Grammar correction.
* **Type "pause"** -- the hook denies continuation so the orchestrator
  waits for further direction.

This is intentionally NON-BLOCKING: the default on timeout is *always*
``allow``, so the system never stalls waiting for a human.

Configuration (via behavior YAML ``config:``)::

    timeout: 15          # seconds before auto-continue
    enabled: true        # set false to skip the gate entirely
    show_plan: true      # include the full plan text in the prompt
"""

from __future__ import annotations

from typing import Any, Callable

try:
    from amplifier_core.models import HookResult  # type: ignore[assignment]
except ImportError:  # standalone / test usage
    from dataclasses import dataclass

    @dataclass
    class HookResult:  # type: ignore[no-redef]
        action: str = "continue"
        data: dict[str, Any] | None = None
        reason: str | None = None
        context_injection: str | None = None
        context_injection_role: str = "system"
        ephemeral: bool = False
        approval_prompt: str | None = None
        approval_options: list[str] | None = None
        approval_timeout: float = 300.0
        approval_default: str = "deny"
        suppress_output: bool = False
        user_message: str | None = None
        user_message_level: str = "info"


__amplifier_module_type__ = "hook"

_CONTINUE = HookResult(action="continue")


class IDDConfirmationGate:
    """Presents the Layer 2 plan with a timed confirmation window.

    The gate uses Amplifier's ``ask_user`` action which routes through
    the coordinator's approval system.  Key settings on the returned
    ``HookResult``:

    * ``approval_timeout`` -- seconds before auto-decision (default 15).
    * ``approval_default`` -- always ``"allow"`` so execution continues.
    * ``approval_options`` -- ``["continue", "edit", "pause"]``.

    If the user replies:

    * Anything matching ``pause|stop|wait|hold`` -> ``action="deny"``
      so the orchestrator halts and waits for new direction.
    * Any other text -> ``action="modify"`` with the user's text in
      ``data["user_correction"]`` so the orchestrator can apply a
      Grammar correction before proceeding.
    * No reply (timeout) -> the approval system returns ``"allow"``
      automatically and the hook resolves as ``action="continue"``.
    """

    _PAUSE_WORDS = frozenset({"pause", "stop", "wait", "hold"})

    def __init__(self, coordinator: Any, config: dict[str, Any]) -> None:
        self._coordinator = coordinator
        self._timeout: float = float(config.get("timeout", 15))
        self._enabled: bool = bool(config.get("enabled", True))
        self._show_plan: bool = bool(config.get("show_plan", True))

    # ------------------------------------------------------------------
    # Hook handler -- registered on ``idd:composition_ready``
    # ------------------------------------------------------------------
    async def handle_composition_ready(
        self,
        event: str,
        data: dict[str, Any],
    ) -> HookResult:
        """Present the plan and open the timed confirmation window."""
        if not self._enabled:
            return _CONTINUE

        plan = data.get("plan", "")
        prompt_parts = []

        if self._show_plan and plan:
            prompt_parts.append(plan)

        prompt_parts.append(
            f"\nProceeding in {int(self._timeout)}s.  "
            "Reply to adjust direction, or type 'pause' to hold."
        )

        return HookResult(
            action="ask_user",
            approval_prompt="\n".join(prompt_parts),
            approval_options=["continue", "edit", "pause"],
            approval_timeout=self._timeout,
            approval_default="allow",  # <-- NON-BLOCKING: always continue on timeout
        )

    # ------------------------------------------------------------------
    # Post-approval handler -- registered on ``idd:confirmation_response``
    # ------------------------------------------------------------------
    async def handle_confirmation_response(
        self,
        event: str,
        data: dict[str, Any],
    ) -> HookResult:
        """Process the user's reply (if any) after the confirmation window.

        The orchestrator emits ``idd:confirmation_response`` with::

            {"response": str | None, "timed_out": bool}

        This handler translates the response into an actionable
        HookResult that the orchestrator checks before proceeding.
        """
        response: str | None = data.get("response")
        timed_out: bool = data.get("timed_out", True)

        # Timeout or empty -> continue (the default path)
        if timed_out or not response:
            return _CONTINUE

        response_lower = response.strip().lower()

        # Pause words -> deny so the orchestrator halts
        if response_lower in self._PAUSE_WORDS:
            return HookResult(
                action="deny",
                reason="User requested pause at Layer 2 confirmation gate.",
                user_message="Paused. Provide new direction when ready.",
                user_message_level="info",
            )

        # "continue" / "yes" / "ok" -> proceed unchanged
        if response_lower in {"continue", "yes", "ok", "y", "proceed", "go"}:
            return _CONTINUE

        # Anything else is a correction / redirect

        # Write CorrectionRecord to GrammarState
        try:
            from datetime import datetime, timezone

            grammar_state = self._coordinator.get_capability("idd.grammar_state")
            if grammar_state is not None:
                from amplifier_module_tool_idd.grammar import CorrectionRecord

                old_goal = "(unknown)"
                decomp = getattr(grammar_state, "decomposition", None)
                if decomp is not None:
                    intent = getattr(decomp, "intent", None)
                    if intent is not None:
                        old_goal = getattr(intent, "goal", "(unknown)")
                record = CorrectionRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    primitive="intent",
                    old_value=old_goal,
                    new_value=response[:500],
                    reason="User direction at Layer 2 confirmation",
                )
                grammar_state.corrections.append(record)
        except Exception:
            pass  # Corrections are observability, never crash the pipeline

        # Emit idd:correction event
        try:
            await self._coordinator.hooks.emit(
                "idd:correction",
                {
                    "primitive": "intent",
                    "reason": response[:200],
                },
            )
        except Exception:
            pass

        return HookResult(
            action="modify",
            data={"user_correction": response},
            reason=f"User provided direction at Layer 2: {response[:200]}",
            user_message=f"Applying adjustment: {response[:200]}",
            user_message_level="info",
        )


# ======================================================================
# Module entry point
# ======================================================================


async def mount(
    coordinator: Any,
    config: dict[str, Any] | None = None,
) -> Callable[[], None] | None:
    """Mount the IDD confirmation gate hook.

    Registers two handlers:

    1. ``idd:composition_ready`` at **priority 7** (after grammar-inject
       at 3, before events at 10) -- opens the timed confirmation window.
    2. ``idd:confirmation_response`` at **priority 7** -- processes the
       user's reply and returns continue / modify / deny.
    """
    config = config or {}
    gate = IDDConfirmationGate(coordinator, config)

    unreg_ready = coordinator.hooks.register(
        "idd:composition_ready",
        gate.handle_composition_ready,
        priority=7,
        name="idd-confirmation-ready",
    )
    unreg_response = coordinator.hooks.register(
        "idd:confirmation_response",
        gate.handle_confirmation_response,
        priority=7,
        name="idd-confirmation-response",
    )

    def cleanup() -> None:
        unreg_ready()
        unreg_response()

    return cleanup
