"""IDD Grammar injection hook - injects Grammar state into LLM context per turn.

Runs at priority 3 on the ``prompt:submit`` event (before tool-policy at 5) so
the LLM sees the current Grammar state when processing each prompt.  Uses
*ephemeral* injection so the state is per-turn and never added to permanent
conversation history.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

try:
    from amplifier_core.models import HookResult  # type: ignore[assignment]
except ImportError:  # pragma: no cover - standalone / test environments
    from dataclasses import dataclass

    @dataclass
    class HookResult:
        """Minimal HookResult-compatible fallback for standalone use."""

        action: str = "continue"
        data: dict[str, Any] | None = None
        reason: str | None = None
        context_injection: str | None = None
        context_injection_role: str = "system"
        ephemeral: bool = False
        user_message: str | None = None
        user_message_level: str = "info"


__amplifier_module_type__ = "hook"

log = logging.getLogger(__name__)


class GrammarInjectionHook:
    """Injects IDD Grammar state into the LLM context per turn.

    Runs at priority 3 (before tool-policy at 5) so the LLM sees Grammar
    state when processing the prompt.  Uses ephemeral injection - the state
    is per-turn, not added to permanent history.
    """

    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    async def handle_prompt(self, event: str, data: dict[str, Any]) -> HookResult:
        """Inject Grammar state on each prompt submission."""
        try:
            grammar_state = self._coordinator.get_capability("idd.grammar_state")
            if grammar_state is None:
                return HookResult(action="continue")

            if grammar_state.decomposition is None:
                return HookResult(action="continue")

            injection = self._build_injection(grammar_state)
            if not injection:
                return HookResult(action="continue")

            return HookResult(
                action="inject_context",
                context_injection=injection,
                context_injection_role="system",
                ephemeral=True,
            )
        except Exception:
            log.debug("idd-grammar-inject: failed to build injection", exc_info=True)
            return HookResult(action="continue")

    # ------------------------------------------------------------------
    # Injection builder
    # ------------------------------------------------------------------

    def _build_injection(self, grammar_state: Any) -> str:
        """Build the Grammar state injection text.

        Returns an empty string when there is nothing meaningful to inject.
        """
        parts: list[str] = ["[IDD GRAMMAR STATE]"]

        decomposition = grammar_state.decomposition
        if not decomposition:
            return ""

        # -- Intent & criteria ------------------------------------------------
        parts.append(f"Intent: {decomposition.intent.goal}")

        criteria: list[str] = getattr(decomposition.intent, "success_criteria", None) or []
        if criteria:
            parts.append("Success Criteria:")
            criteria_status: list[Any] = getattr(grammar_state, "criteria_status", None) or []
            for idx, criterion in enumerate(criteria):
                status = self._resolve_criterion_status(criteria_status, idx)
                parts.append(f"  - [{status}] {criterion}")

        # -- Progress ---------------------------------------------------------
        status_label: str = getattr(grammar_state, "status", "unknown")
        steps_done: int = getattr(grammar_state, "steps_completed", 0)
        steps_total: int = getattr(grammar_state, "steps_total", 0)
        parts.append(f"Status: {status_label} ({steps_done}/{steps_total} steps)")

        # -- Corrections (last 3) --------------------------------------------
        corrections: list[Any] = getattr(grammar_state, "corrections", None) or []
        if corrections:
            parts.append(f"Corrections: {len(corrections)} applied")
            for corr in corrections[-3:]:
                primitive = getattr(corr, "primitive", "?")
                reason = getattr(corr, "reason", "")
                parts.append(f"  - {primitive}: {reason}")

        return "\n".join(parts)

    @staticmethod
    def _resolve_criterion_status(
        criteria_status: list[Any],
        idx: int,
    ) -> str:
        """Return a human-readable status label for criterion at *idx*."""
        if not criteria_status or idx >= len(criteria_status):
            return "?"
        cs = criteria_status[idx]
        passed = getattr(cs, "passed", None)
        if passed is True:
            return "PASS"
        if passed is False:
            return "FAIL"
        return "pending"


# ------------------------------------------------------------------
# Module entry point
# ------------------------------------------------------------------


async def mount(
    coordinator: Any,
    config: dict[str, Any] | None = None,
) -> Callable[[], None]:
    """Mount the Grammar injection hook.

    Registers on ``prompt:submit`` at the configured priority (default 3).

    Returns a *cleanup* callable that unregisters the handler.
    """
    config = config or {}
    priority: int = config.get("priority", 3)

    hook = GrammarInjectionHook(coordinator)
    unreg = coordinator.hooks.register(
        "prompt:submit",
        hook.handle_prompt,
        priority=priority,
        name="idd-grammar-inject",
    )

    def cleanup() -> None:
        try:
            unreg()
        except Exception:
            log.debug("idd-grammar-inject: error during cleanup", exc_info=True)

    return cleanup
