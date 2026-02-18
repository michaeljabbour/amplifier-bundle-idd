"""IDD Compiler — Compiles a Decomposition into an executable YAML recipe.

Translates the five-primitive decomposition into the Amplifier recipe
schema (v1.7.0) so the orchestrator can execute steps through the
standard recipe runner or hand them off to agents.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from .grammar import AgentAssignment, Decomposition


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------


class IDDCompiler:
    """Compiles a :class:`Decomposition` into an executable recipe dict."""

    # -- public API -----------------------------------------------------------

    def compile(self, decomposition: Decomposition) -> dict[str, Any]:
        """Convert a *decomposition* into a recipe dict.

        The returned dict conforms to Amplifier recipe schema v1.7.0 and
        can be serialised with :func:`yaml.dump` or executed directly.

        Parameters
        ----------
        decomposition:
            The five-primitive decomposition produced by the parser.

        Returns
        -------
        dict
            A recipe dict with ``name``, ``description``, ``steps``,
            and ``metadata`` keys.
        """
        groups = self._detect_parallelism(decomposition.agents)

        steps: list[dict[str, Any]] = []
        prev_step_names: list[str] = []

        for group in groups:
            current_names: list[str] = []
            for agent in group:
                step_name = self._step_name(agent.name, len(steps))
                step = self._build_step(
                    agent=agent,
                    step_name=step_name,
                    depends_on=list(prev_step_names),
                    context_includes=self._context_refs(prev_step_names),
                )
                steps.append(step)
                current_names.append(step_name)
            prev_step_names = current_names

        recipe: dict[str, Any] = {
            "name": self._recipe_name(decomposition),
            "description": decomposition.intent.goal,
            "steps": steps,
        }

        # -- Approval gate from trigger.confirmation --------------------------
        if decomposition.trigger.confirmation == "human":
            recipe["approval"] = {
                "required": True,
                "message": (
                    f"This recipe will: {decomposition.intent.goal}\nPlease approve to proceed."
                ),
            }

        # -- Metadata (intent + confidence) -----------------------------------
        recipe["metadata"] = {
            "idd": {
                "intent": decomposition.intent.goal,
                "success_criteria": decomposition.intent.success_criteria,
                "confidence": decomposition.confidence,
                "scope_in": decomposition.intent.scope_in,
                "scope_out": decomposition.intent.scope_out,
                "behaviors": [b.name for b in decomposition.behaviors],
            },
        }

        return recipe

    def compile_to_yaml(self, decomposition: Decomposition) -> str:
        """Compile and return a YAML string.

        Parameters
        ----------
        decomposition:
            The five-primitive decomposition produced by the parser.

        Returns
        -------
        str
            A YAML-formatted string of the compiled recipe.
        """
        recipe = self.compile(decomposition)
        return yaml.dump(
            recipe,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    # -- step building --------------------------------------------------------

    @staticmethod
    def _build_step(
        agent: AgentAssignment,
        step_name: str,
        depends_on: list[str],
        context_includes: list[str],
    ) -> dict[str, Any]:
        """Build a single recipe step dict from an :class:`AgentAssignment`.

        Parameters
        ----------
        agent:
            The agent assignment to turn into a step.
        step_name:
            Unique name for this step within the recipe.
        depends_on:
            Names of steps that must complete before this one.
        context_includes:
            Template expressions (``{{steps.X.result}}``) to inject into
            this step's context.

        Returns
        -------
        dict
            A recipe step dict.
        """
        step: dict[str, Any] = {
            "name": step_name,
            "agent": agent.name,
            "instruction": agent.instruction,
        }

        if depends_on:
            step["depends_on"] = depends_on

        if context_includes:
            step["context"] = {"include": context_includes}

        if agent.role:
            step["role"] = agent.role

        return step

    # -- parallelism detection ------------------------------------------------

    @staticmethod
    def _detect_parallelism(
        agents: list[AgentAssignment],
    ) -> list[list[AgentAssignment]]:
        """Group agents into parallel execution groups.

        Agents whose instructions contain explicit parallel markers
        (``parallel:``, ``concurrently``, ``at the same time``) or whose
        names are identical are grouped together.  All other agents are
        treated as sequential single-element groups.

        Parameters
        ----------
        agents:
            Flat list of agent assignments from the decomposition.

        Returns
        -------
        list[list[AgentAssignment]]
            Ordered list of groups.  Agents within a group may run
            concurrently; groups execute sequentially.
        """
        if not agents:
            return []

        _PARALLEL_PATTERN = re.compile(
            r"\b(parallel|concurrent(?:ly)?|at the same time|simultaneously)\b",
            re.IGNORECASE,
        )

        groups: list[list[AgentAssignment]] = []
        current_group: list[AgentAssignment] = []

        for i, agent in enumerate(agents):
            if current_group:
                prev = current_group[-1]
                # Same agent name or explicit parallel marker → same group
                is_parallel = (
                    agent.name == prev.name
                    or _PARALLEL_PATTERN.search(agent.instruction) is not None
                    or _PARALLEL_PATTERN.search(prev.instruction) is not None
                )
                if is_parallel:
                    current_group.append(agent)
                else:
                    groups.append(current_group)
                    current_group = [agent]
            else:
                current_group = [agent]

        if current_group:
            groups.append(current_group)

        return groups

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _step_name(agent_name: str, index: int) -> str:
        """Generate a unique, slug-safe step name."""
        slug = re.sub(r"[^a-z0-9]+", "-", agent_name.lower()).strip("-") or "step"
        return f"{slug}-{index}"

    @staticmethod
    def _recipe_name(decomposition: Decomposition) -> str:
        """Derive a short recipe name from the intent goal."""
        goal = decomposition.intent.goal
        # Take first 60 chars, slugify
        slug = re.sub(r"[^a-z0-9]+", "-", goal[:60].lower()).strip("-")
        return f"idd-{slug}" if slug else "idd-task"

    @staticmethod
    def _context_refs(step_names: list[str]) -> list[str]:
        """Build ``{{steps.<name>.result}}`` template references."""
        return [f"{{{{steps.{name}.result}}}}" for name in step_names]
