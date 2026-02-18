"""IDD Parser — Layer 1→2 decomposition via LLM.

Takes a natural-language prompt and decomposes it into the five IDD
primitives (Intent, Trigger, Agent, Context, Behavior) by asking an LLM
to produce structured JSON.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .grammar import (
    AgentAssignment,
    BehaviorReference,
    ContextRequirement,
    Decomposition,
    IntentPrimitive,
    TriggerPrimitive,
)

# Conditional import — ChatRequest/Message come from amplifier-core,
# but we guard the import so the module can be tested in isolation.
try:
    from amplifier_core.message_models import ChatRequest, Message  # pyright: ignore[reportAttributeAccessIssue]
except ImportError:  # pragma: no cover
    ChatRequest = None  # type: ignore[assignment,misc]
    Message = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are an IDD (Intent-Driven Design) parser.
Decompose the user's input into five orthogonal primitives.

Output **only** valid JSON (no markdown fences, no commentary) matching this schema:

{{
  "intent": {{
    "goal": "<concise goal statement>",
    "success_criteria": ["<criterion 1>", "..."],
    "scope_in": ["<in-scope item>"],
    "scope_out": ["<out-of-scope item>"],
    "values": ["<guiding value>"]
  }},
  "trigger": {{
    "activation": "<what triggers this task>",
    "pre_conditions": ["<condition>"],
    "confirmation": "auto" | "human" | "none"
  }},
  "agents": [
    {{
      "name": "<agent name from available list, or 'self'>",
      "role": "<short role label>",
      "instruction": "<what the agent should do>"
    }}
  ],
  "context": {{
    "auto_detected": ["<context inferred from input>"],
    "provided": ["<context explicitly given>"],
    "to_discover": ["<context that must be gathered>"]
  }},
  "behaviors": [
    {{"name": "<behavior name>"}}
  ],
  "confidence": <float 0.0-1.0>
}}

Available agents: {available_agents}

Rules:
- Pick agents from the available list when they fit; use "self" for work
  the orchestrator can handle directly.
- If the task is simple, a single agent is fine.
- Set confirmation to "human" when the task is destructive or irreversible.
- confidence reflects how well-defined the input is (vague → low, precise → high).
"""

_DEFAULT_TEMPERATURE = 0.3


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class IDDParser:
    """Decomposes natural language into five IDD primitives using an LLM."""

    # -- public API -----------------------------------------------------------

    async def parse(
        self,
        prompt: str,
        providers: dict[str, Any],
        available_agents: list[str],
    ) -> Decomposition:
        """Call an LLM provider to decompose *prompt* into a :class:`Decomposition`.

        Parameters
        ----------
        prompt:
            The raw user input (Layer 1 text).
        providers:
            Mapping of provider name → provider instance.  The first
            available provider is used.
        available_agents:
            Names of agents the coordinator has access to.

        Returns
        -------
        Decomposition
            Parsed five-primitive decomposition.  On error a minimal
            fallback decomposition is returned so execution never crashes.
        """
        provider = self._pick_provider(providers)
        if provider is None:
            logger.warning("IDDParser: no provider available — returning fallback")
            return self._fallback_decomposition(prompt, reason="no provider available")

        request = self._build_chat_request(prompt, available_agents)
        try:
            response = await provider.complete(request)
            raw_content = response.content or ""
            # response.content may be a string or a list of content blocks
            if isinstance(raw_content, list):
                raw_text = "".join(getattr(block, "text", str(block)) for block in raw_content)
            else:
                raw_text = str(raw_content)
            return self._parse_response(raw_text, prompt)
        except Exception:
            logger.exception("IDDParser: LLM call failed — returning fallback")
            return self._fallback_decomposition(prompt, reason="LLM call failed")

    # -- request building -----------------------------------------------------

    def _build_chat_request(
        self,
        prompt: str,
        available_agents: list[str],
    ) -> Any:
        """Build a :class:`ChatRequest` for the decomposition LLM call."""
        if ChatRequest is None or Message is None:
            raise RuntimeError("amplifier_core is not installed — cannot build ChatRequest")

        agents_str = ", ".join(available_agents) if available_agents else "(none)"
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(available_agents=agents_str)

        return ChatRequest(
            messages=[
                Message(role="system", content=system_prompt),
                Message(role="user", content=prompt),
            ],
            temperature=_DEFAULT_TEMPERATURE,
        )

    # -- response parsing -----------------------------------------------------

    def _parse_response(self, raw_text: str, original_prompt: str) -> Decomposition:
        """Parse LLM JSON output into a :class:`Decomposition`.

        Tolerates markdown code fences and minor formatting issues.
        """
        cleaned = self._extract_json(raw_text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("IDDParser: failed to parse JSON from LLM response")
            return self._fallback_decomposition(original_prompt, reason="malformed JSON from LLM")

        return self._dict_to_decomposition(data, original_prompt)

    @staticmethod
    def _extract_json(text: str) -> str:
        """Strip optional markdown fences and leading/trailing whitespace."""
        text = text.strip()
        # Remove ```json ... ``` wrappers
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if fence_match:
            return fence_match.group(1).strip()
        return text

    def _dict_to_decomposition(self, data: dict, raw_input: str) -> Decomposition:
        """Safely convert a parsed dict into a :class:`Decomposition`.

        Missing or malformed keys fall back to sensible defaults.
        """
        intent_d = data.get("intent", {})
        intent = IntentPrimitive(
            goal=intent_d.get("goal", raw_input[:200]),
            success_criteria=_as_str_list(intent_d.get("success_criteria")),
            scope_in=_as_str_list(intent_d.get("scope_in")),
            scope_out=_as_str_list(intent_d.get("scope_out")),
            values=_as_str_list(intent_d.get("values")),
        )

        trigger_d = data.get("trigger", {})
        trigger = TriggerPrimitive(
            activation=trigger_d.get("activation", "user request"),
            pre_conditions=_as_str_list(trigger_d.get("pre_conditions")),
            confirmation=trigger_d.get("confirmation", "auto"),
        )

        agents = [
            AgentAssignment(
                name=a.get("name", "self"),
                role=a.get("role", "executor"),
                instruction=a.get("instruction", ""),
            )
            for a in data.get("agents", [])
            if isinstance(a, dict)
        ]
        # Ensure at least one agent
        if not agents:
            agents = [
                AgentAssignment(
                    name="self",
                    role="executor",
                    instruction=raw_input[:500],
                )
            ]

        ctx_d = data.get("context", {})
        context = ContextRequirement(
            auto_detected=_as_str_list(ctx_d.get("auto_detected")),
            provided=_as_str_list(ctx_d.get("provided")),
            to_discover=_as_str_list(ctx_d.get("to_discover")),
        )

        behaviors = [
            BehaviorReference(name=b.get("name", "default"))
            for b in data.get("behaviors", [])
            if isinstance(b, dict) and b.get("name")
        ]

        confidence = data.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.0
        confidence = max(0.0, min(1.0, float(confidence)))

        return Decomposition(
            intent=intent,
            trigger=trigger,
            agents=agents,
            context=context,
            behaviors=behaviors,
            raw_input=raw_input,
            confidence=confidence,
        )

    # -- fallback -------------------------------------------------------------

    @staticmethod
    def _fallback_decomposition(prompt: str, *, reason: str) -> Decomposition:
        """Return a minimal decomposition when parsing fails.

        This guarantees the orchestrator always has *something* to work
        with, even if the LLM call errors out.
        """
        return Decomposition(
            intent=IntentPrimitive(
                goal=prompt[:200],
                success_criteria=["Task completed successfully"],
            ),
            trigger=TriggerPrimitive(activation="user request"),
            agents=[
                AgentAssignment(
                    name="self",
                    role="executor",
                    instruction=prompt[:500],
                ),
            ],
            context=ContextRequirement(),
            behaviors=[],
            raw_input=prompt,
            confidence=0.0,
        )

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _pick_provider(providers: dict[str, Any]) -> Any | None:
        """Return the first available provider, or *None*."""
        return next(iter(providers.values()), None) if providers else None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _as_str_list(value: Any) -> list[str]:
    """Coerce *value* to a list of strings, tolerating ``None`` and scalars."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if v is not None]
    return []
