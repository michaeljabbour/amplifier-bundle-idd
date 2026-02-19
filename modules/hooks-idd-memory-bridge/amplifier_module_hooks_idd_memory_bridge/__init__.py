"""IDD Memory Bridge — persists decomposition results to LetsGo memory.

Subscribes to ``idd:intent_resolved`` and ``idd:correction`` events.
When LetsGo's ``memory.store`` capability is available, stores results
as persistent memories with proper categories, concepts, and tags.

**Graceful degradation**: If LetsGo is not composed (``memory.store``
capability absent), all handlers silently return ``continue``.
No imports from LetsGo or any other bundle.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

try:
    from amplifier_core.models import HookResult  # type: ignore[assignment]
except ImportError:  # pragma: no cover
    from dataclasses import dataclass

    @dataclass
    class HookResult:
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

_CONTINUE = HookResult(action="continue")


class IDDMemoryBridge:
    """Bridges IDD events to LetsGo's persistent memory store.

    Discovers ``memory.store`` capability at event time (not mount time)
    so the bridge works regardless of module load order.
    """

    def __init__(self, coordinator: Any, config: dict[str, Any]) -> None:
        self._coordinator = coordinator
        self._enabled: bool = bool(config.get("enabled", True))

    def _get_memory_store(self) -> Any | None:
        """Discover memory.store capability. Returns None if LetsGo absent."""
        try:
            return self._coordinator.get_capability("memory.store")
        except Exception:
            return None

    async def _store_memory(
        self,
        content: str,
        *,
        title: str,
        category: str,
        importance: float,
        concepts: list[str],
        tags: list[str],
        mem_type: str = "decision",
    ) -> None:
        """Store a memory via the memory.store capability if available."""
        store = self._get_memory_store()
        if store is None:
            return
        try:
            # memory.store is typically a MemoryStore instance with a store() method
            # Use the tool-memory-store interface: store_memory operation
            if hasattr(store, "store"):
                await store.store(
                    content=content,
                    title=title,
                    category=category,
                    importance=importance,
                    concepts=concepts,
                    tags=tags,
                    type=mem_type,
                )
            elif callable(store):
                import inspect

                result = store(
                    operation="store_memory",
                    content=content,
                    title=title,
                    category=category,
                    importance=importance,
                    concepts=concepts,
                    tags=tags,
                    type=mem_type,
                )
                if inspect.isawaitable(result):
                    await result
        except Exception:
            log.debug("idd-memory-bridge: failed to store memory", exc_info=True)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def handle_intent_resolved(self, event: str, data: dict[str, Any]) -> HookResult:
        """Store resolved intent as a persistent memory."""
        if not self._enabled:
            return _CONTINUE

        try:
            status = data.get("status", "unknown")
            summary = data.get("summary", "")
            criteria = data.get("success_criteria", [])

            # Build a rich memory content
            parts = [f"IDD Intent Resolved: {summary}", f"Status: {status}"]
            if criteria:
                parts.append("Success Criteria:")
                for c in criteria:
                    icon = "PASS" if c.get("pass") else "FAIL"
                    parts.append(f"  [{icon}] {c.get('name', '?')}")
                    evidence = c.get("evidence", "")
                    if evidence:
                        parts.append(f"    Evidence: {evidence}")

            # Include decomposition if available
            gs = self._coordinator.get_capability("idd.grammar_state")
            if gs and gs.decomposition:
                d = gs.decomposition
                parts.append(f"\nAgents used: {', '.join(a.name for a in d.agents)}")
                if d.intent.scope_out:
                    parts.append(f"Out of scope: {', '.join(d.intent.scope_out)}")
                if gs.corrections:
                    parts.append(f"Corrections applied: {len(gs.corrections)}")

            content = "\n".join(parts)

            await self._store_memory(
                content=content,
                title=f"IDD: {summary[:100]}" if summary else "IDD intent resolved",
                category="decision",
                importance=0.8 if status == "completed" else 0.6,
                concepts=["problem-solution", "what-changed"],
                tags=["idd", "intent-resolved", status],
                mem_type="decision" if status == "completed" else "discovery",
            )
        except Exception:
            log.debug("idd-memory-bridge: error in handle_intent_resolved", exc_info=True)

        return _CONTINUE

    async def handle_correction(self, event: str, data: dict[str, Any]) -> HookResult:
        """Store mid-flight corrections as persistent memories."""
        if not self._enabled:
            return _CONTINUE

        try:
            primitive = data.get("primitive", "unknown")
            reason = data.get("reason", "")

            if not reason:
                return _CONTINUE

            content = (
                f"IDD Mid-Flight Correction\n"
                f"Primitive adjusted: {primitive}\n"
                f"User direction: {reason}"
            )

            await self._store_memory(
                content=content,
                title=f"IDD correction: {primitive} — {reason[:80]}",
                category="learning",
                importance=0.6,
                concepts=["gotcha", "trade-off"],
                tags=["idd", "correction", primitive],
                mem_type="discovery",
            )
        except Exception:
            log.debug("idd-memory-bridge: error in handle_correction", exc_info=True)

        return _CONTINUE


# ------------------------------------------------------------------
# Module entry point
# ------------------------------------------------------------------


async def mount(
    coordinator: Any,
    config: dict[str, Any] | None = None,
) -> Callable[[], None]:
    """Mount the IDD memory bridge hook.

    Registers handlers at priority 12 (after events at 10, before
    reporter at 15) for ``idd:intent_resolved`` and ``idd:correction``.
    """
    config = config or {}
    bridge = IDDMemoryBridge(coordinator, config)

    unreg_resolved = coordinator.hooks.register(
        "idd:intent_resolved",
        bridge.handle_intent_resolved,
        priority=12,
        name="idd-memory-bridge-resolved",
    )
    unreg_correction = coordinator.hooks.register(
        "idd:correction",
        bridge.handle_correction,
        priority=12,
        name="idd-memory-bridge-correction",
    )

    def cleanup() -> None:
        unreg_resolved()
        unreg_correction()

    return cleanup
