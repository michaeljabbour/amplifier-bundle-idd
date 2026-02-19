"""IDD event recorder hook - telemetry and observability for IDD lifecycle events.

Listens to all ``idd:*`` events at priority 10 (non-blocking observer) and
records them in an in-memory log.  The log is exposed via the
``idd.event_log`` capability so other modules (dashboards, exporters, tests)
can inspect it at any time.

Recorded events are defensively truncated to prevent unbounded memory growth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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

# Hard limits to keep the in-memory log bounded.
_MAX_EVENTS = 2000
_MAX_VALUE_LEN = 500


class IDDEventRecorder:
    """Records IDD events for telemetry and observability.

    Each recorded entry contains the event name, an ISO-8601 UTC timestamp,
    and a shallow copy of the event data with values truncated to
    *_MAX_VALUE_LEN* characters.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._max_events: int = config.get("max_events", _MAX_EVENTS)
        self._events: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    async def handle_event(self, event: str, data: dict[str, Any]) -> HookResult:
        """Record any IDD event.  Always returns *continue* - never blocks."""
        try:
            entry: dict[str, Any] = {
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {k: str(v)[:_MAX_VALUE_LEN] for k, v in data.items()},
            }
            self._events.append(entry)

            # Evict oldest events when the log grows beyond the cap.
            if len(self._events) > self._max_events:
                self._events[:] = self._events[-self._max_events :]
        except Exception:
            # Telemetry must never crash the pipeline.
            log.debug("idd-events: failed to record event %s", event, exc_info=True)

        return HookResult(action="continue")


# ------------------------------------------------------------------
# Module entry point
# ------------------------------------------------------------------

_IDD_EVENTS: tuple[str, ...] = (
    "idd:intent_parsed",
    "idd:primitive_matched",
    "idd:composition_ready",
    "idd:correction",
    "idd:progress",
    "idd:intent_resolved",
)


async def mount(
    coordinator: Any,
    config: dict[str, Any] | None = None,
) -> Callable[[], None]:
    """Mount the IDD event recorder hook.

    Registers a single handler for every ``idd:*`` event at priority 10
    and exposes the event log as the ``idd.event_log`` capability.

    Returns a *cleanup* callable that unregisters all handlers.
    """
    config = config or {}
    recorder = IDDEventRecorder(config)

    unregister_fns: list[Callable[[], None]] = []
    for event in _IDD_EVENTS:
        # Register composition_ready at priority 5 (before confirmation gate
        # at 7) so the recorder sees the event even if ask_user blocks
        # further handlers.
        event_priority = 5 if event == "idd:composition_ready" else 10
        unreg = coordinator.hooks.register(
            event,
            recorder.handle_event,
            priority=event_priority,
            name=f"idd-events-{event}",
        )
        unregister_fns.append(unreg)

    # Expose the log for inspection by other modules / tests.
    try:
        coordinator.register_capability("idd.event_log", recorder._events)
    except Exception:
        log.debug(
            "idd-events: could not register idd.event_log capability",
            exc_info=True,
        )

    def cleanup() -> None:
        for unreg in unregister_fns:
            try:
                unreg()
            except Exception:
                log.debug("idd-events: error during cleanup", exc_info=True)

    return cleanup
