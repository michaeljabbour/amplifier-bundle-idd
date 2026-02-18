"""IDD Layer 2-to-1 reporter hook - translates execution state to human-readable output.

Reports progress against the user's original intent and success criteria, not
internal machinery state.  Non-blocking observer at priority 15.

Listens to:
- ``idd:composition_ready`` - the decomposition plan
- ``idd:progress``          - step completion progress
- ``idd:correction``        - mid-flight corrections
- ``idd:intent_resolved``   - final outcome with criteria verdicts
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

# Continue-only sentinel to avoid repeated allocation.
_CONTINUE = HookResult(action="continue")


class IDDReporter:
    """Layer 2-to-1 reporter - translates execution state to human-readable output.

    Reports progress against the user's original intent and success criteria,
    not internal machinery state.  Non-blocking observer at priority 15.
    """

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def handle_composition_ready(self, event: str, data: dict[str, Any]) -> HookResult:
        """Report the decomposition plan to the user."""
        try:
            plan = data.get("plan", "")
            if not plan:
                return _CONTINUE
            return HookResult(
                action="continue",
                user_message=f"\U0001f4cb IDD Plan:\n{plan}",
                user_message_level="info",
            )
        except Exception:
            log.debug("idd-reporter: error in composition_ready", exc_info=True)
            return _CONTINUE

    async def handle_progress(self, event: str, data: dict[str, Any]) -> HookResult:
        """Report step completion progress."""
        try:
            step = data.get("step", "unknown")
            completed = data.get("completed", 0)
            total = data.get("total", 0)
            return HookResult(
                action="continue",
                user_message=f"\u23f3 Step {completed}/{total}: {step} completed",
                user_message_level="info",
            )
        except Exception:
            log.debug("idd-reporter: error in progress", exc_info=True)
            return _CONTINUE

    async def handle_correction(self, event: str, data: dict[str, Any]) -> HookResult:
        """Report mid-flight corrections."""
        try:
            primitive = data.get("primitive", "unknown")
            reason = data.get("reason", "")
            return HookResult(
                action="continue",
                user_message=(
                    f"\U0001f504 Correction: {primitive} updated"
                    + (f" \u2014 {reason}" if reason else "")
                ),
                user_message_level="info",
            )
        except Exception:
            log.debug("idd-reporter: error in correction", exc_info=True)
            return _CONTINUE

    async def handle_resolved(self, event: str, data: dict[str, Any]) -> HookResult:
        """Report final intent resolution with success criteria verdicts."""
        try:
            status = data.get("status", "unknown")
            summary = data.get("summary", "")
            criteria: list[dict[str, Any]] = data.get("success_criteria", [])

            parts: list[str] = []

            if status == "completed":
                parts.append("\u2705 Intent resolved successfully")
            else:
                parts.append(f"\u274c Intent {status}")

            if criteria:
                parts.append("Success Criteria:")
                for criterion in criteria:
                    icon = "\u2705" if criterion.get("pass") else "\u274c"
                    parts.append(f"  {icon} {criterion.get('name', '?')}")

            if summary:
                parts.append(f"\n{summary}")

            return HookResult(
                action="continue",
                user_message="\n".join(parts),
                user_message_level="info",
            )
        except Exception:
            log.debug("idd-reporter: error in resolved", exc_info=True)
            return _CONTINUE


# ------------------------------------------------------------------
# Module entry point
# ------------------------------------------------------------------


async def mount(
    coordinator: Any,
    config: dict[str, Any] | None = None,
) -> Callable[[], None]:
    """Mount the IDD reporter hook.

    Registers handlers for composition, progress, correction, and resolution
    events at the configured priority (default 15).

    Returns a *cleanup* callable that unregisters all handlers.
    """
    config = config or {}
    priority: int = config.get("priority", 15)

    reporter = IDDReporter()
    unregister_fns: list[Callable[[], None]] = []

    handlers: dict[str, Callable[..., Any]] = {
        "idd:composition_ready": reporter.handle_composition_ready,
        "idd:progress": reporter.handle_progress,
        "idd:correction": reporter.handle_correction,
        "idd:intent_resolved": reporter.handle_resolved,
    }

    for event_name, handler in handlers.items():
        unreg = coordinator.hooks.register(
            event_name,
            handler,
            priority=priority,
            name=f"idd-reporter-{event_name}",
        )
        unregister_fns.append(unreg)

    def cleanup() -> None:
        for unreg in unregister_fns:
            try:
                unreg()
            except Exception:
                log.debug("idd-reporter: error during cleanup", exc_info=True)

    return cleanup
