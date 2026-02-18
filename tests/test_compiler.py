"""Tests for the IDD Compiler (Decomposition -> YAML recipe)."""

from __future__ import annotations

import yaml

from amplifier_module_tool_idd.compiler import IDDCompiler
from amplifier_module_tool_idd.grammar import (
    AgentAssignment,
    BehaviorReference,
    ContextRequirement,
    Decomposition,
    IntentPrimitive,
    TriggerPrimitive,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decomposition(
    agents: list[AgentAssignment] | None = None,
    confirmation: str = "auto",
    goal: str = "Implement feature X",
    behaviors: list[BehaviorReference] | None = None,
    success_criteria: list[str] | None = None,
) -> Decomposition:
    """Build a Decomposition with configurable agents and trigger."""
    return Decomposition(
        intent=IntentPrimitive(
            goal=goal,
            success_criteria=success_criteria or ["Tests pass", "Code reviewed"],
            scope_in=["module A"],
            scope_out=["module B"],
        ),
        trigger=TriggerPrimitive(activation="user request", confirmation=confirmation),
        agents=agents
        if agents is not None
        else [
            AgentAssignment(name="explorer", role="scout", instruction="Explore the codebase"),
            AgentAssignment(name="builder", role="impl", instruction="Build the feature"),
        ],
        context=ContextRequirement(
            auto_detected=["Python project"],
            provided=["spec.md"],
            to_discover=["current tests"],
        ),
        behaviors=behaviors or [],
        raw_input="Implement feature X",
        confidence=0.9,
    )


# ===================================================================
# Basic recipe structure
# ===================================================================


class TestCompilerBasicStructure:
    def test_compile_returns_dict(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert isinstance(result, dict)

    def test_recipe_has_name(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert "name" in result
        assert result["name"].startswith("idd-")

    def test_recipe_has_description(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert result["description"] == "Implement feature X"

    def test_recipe_has_steps_key(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert "steps" in result
        assert isinstance(result["steps"], list)

    def test_step_count_matches_agents(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert len(result["steps"]) == 2

    def test_recipe_has_metadata(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert "metadata" in result
        assert "idd" in result["metadata"]


# ===================================================================
# Step fields
# ===================================================================


class TestCompilerStepFields:
    def test_step_has_required_fields(self):
        """Every step must have name, agent, instruction."""
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        for step in result["steps"]:
            assert "name" in step, f"Step missing 'name': {step}"
            assert "agent" in step, f"Step missing 'agent': {step}"
            assert "instruction" in step, f"Step missing 'instruction': {step}"

    def test_step_agent_matches_assignment(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert result["steps"][0]["agent"] == "explorer"
        assert result["steps"][1]["agent"] == "builder"

    def test_step_instruction_matches_assignment(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert result["steps"][0]["instruction"] == "Explore the codebase"
        assert result["steps"][1]["instruction"] == "Build the feature"

    def test_step_has_role(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert result["steps"][0]["role"] == "scout"
        assert result["steps"][1]["role"] == "impl"

    def test_step_name_is_slug(self):
        """Step names should be slug-safe (lowercase, hyphens, digits)."""
        compiler = IDDCompiler()
        agents = [AgentAssignment(name="Zen Architect!", role="r", instruction="i")]
        result = compiler.compile(_decomposition(agents=agents))
        step_name = result["steps"][0]["name"]
        assert step_name == step_name.lower()
        assert " " not in step_name
        assert "!" not in step_name


# ===================================================================
# Sequential dependency chain
# ===================================================================


class TestCompilerSequentialDeps:
    def test_first_step_no_depends_on(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        first = result["steps"][0]
        assert "depends_on" not in first

    def test_second_step_depends_on_first(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        second = result["steps"][1]
        assert "depends_on" in second
        assert result["steps"][0]["name"] in second["depends_on"]

    def test_three_sequential_agents_chain(self):
        agents = [
            AgentAssignment(name="a", role="r1", instruction="do a"),
            AgentAssignment(name="b", role="r2", instruction="do b"),
            AgentAssignment(name="c", role="r3", instruction="do c"),
        ]
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(agents=agents))
        steps = result["steps"]
        assert len(steps) == 3
        # a has no deps
        assert "depends_on" not in steps[0]
        # b depends on a
        assert steps[0]["name"] in steps[1]["depends_on"]
        # c depends on b
        assert steps[1]["name"] in steps[2]["depends_on"]


# ===================================================================
# Parallel agents
# ===================================================================


class TestCompilerParallelism:
    def test_same_name_agents_grouped(self):
        """Agents with the same name are grouped as parallel."""
        agents = [
            AgentAssignment(name="explorer", role="r1", instruction="search area A"),
            AgentAssignment(name="explorer", role="r2", instruction="search area B"),
            AgentAssignment(name="builder", role="r3", instruction="build it"),
        ]
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(agents=agents))
        steps = result["steps"]
        # Two explorers should share the same depends_on (none, as they're first)
        assert "depends_on" not in steps[0]
        assert "depends_on" not in steps[1]
        # Builder depends on both explorers
        assert len(steps[2].get("depends_on", [])) == 2

    def test_parallel_keyword_in_instruction(self):
        """Agents with 'parallel' in instruction are grouped together."""
        agents = [
            AgentAssignment(name="a", role="r", instruction="step one"),
            AgentAssignment(name="b", role="r", instruction="run concurrently with a"),
        ]
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(agents=agents))
        steps = result["steps"]
        # Both should be in the same group, so second has no depends_on
        assert "depends_on" not in steps[0]
        assert "depends_on" not in steps[1]

    def test_parallel_agents_share_depends_from_prior(self):
        """Parallel group members all depend on the prior group."""
        # NOTE: avoid parallel-keyword in instructions here -- we rely on
        # same-name grouping only so that setup stays in its own group.
        agents = [
            AgentAssignment(name="setup", role="r", instruction="initial setup"),
            AgentAssignment(name="worker", role="r", instruction="do task A"),
            AgentAssignment(name="worker", role="r", instruction="do task B"),
        ]
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(agents=agents))
        steps = result["steps"]
        # setup is alone in group 1 -- no deps
        assert "depends_on" not in steps[0]
        # Two workers in group 2 -- both depend on setup
        assert steps[0]["name"] in steps[1].get("depends_on", [])
        assert steps[0]["name"] in steps[2].get("depends_on", [])


# ===================================================================
# Context references
# ===================================================================


class TestCompilerContextRefs:
    def test_second_step_has_context_include(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        second = result["steps"][1]
        assert "context" in second
        assert "include" in second["context"]

    def test_context_uses_template_expression(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        second = result["steps"][1]
        includes = second["context"]["include"]
        first_name = result["steps"][0]["name"]
        expected = f"{{{{steps.{first_name}.result}}}}"
        assert expected in includes

    def test_first_step_no_context_include(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        first = result["steps"][0]
        assert "context" not in first


# ===================================================================
# Human confirmation / approval gate
# ===================================================================


class TestCompilerApprovalGate:
    def test_human_confirmation_adds_approval(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(confirmation="human"))
        assert "approval" in result
        assert result["approval"]["required"] is True
        assert "message" in result["approval"]

    def test_auto_confirmation_no_approval(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(confirmation="auto"))
        assert "approval" not in result

    def test_none_confirmation_no_approval(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(confirmation="none"))
        assert "approval" not in result

    def test_approval_message_contains_goal(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(confirmation="human", goal="Delete all data"))
        assert "Delete all data" in result["approval"]["message"]


# ===================================================================
# Intent metadata
# ===================================================================


class TestCompilerMetadata:
    def test_metadata_has_intent(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        idd_meta = result["metadata"]["idd"]
        assert idd_meta["intent"] == "Implement feature X"

    def test_metadata_has_success_criteria(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        idd_meta = result["metadata"]["idd"]
        assert "Tests pass" in idd_meta["success_criteria"]
        assert "Code reviewed" in idd_meta["success_criteria"]

    def test_metadata_has_confidence(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        assert result["metadata"]["idd"]["confidence"] == 0.9

    def test_metadata_has_scope(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition())
        idd_meta = result["metadata"]["idd"]
        assert "module A" in idd_meta["scope_in"]
        assert "module B" in idd_meta["scope_out"]

    def test_metadata_has_behaviors(self):
        behaviors = [BehaviorReference(name="tdd"), BehaviorReference(name="incremental")]
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(behaviors=behaviors))
        assert "tdd" in result["metadata"]["idd"]["behaviors"]
        assert "incremental" in result["metadata"]["idd"]["behaviors"]

    def test_metadata_empty_behaviors(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(behaviors=[]))
        assert result["metadata"]["idd"]["behaviors"] == []


# ===================================================================
# compile_to_yaml()
# ===================================================================


class TestCompileToYaml:
    def test_returns_string(self):
        compiler = IDDCompiler()
        result = compiler.compile_to_yaml(_decomposition())
        assert isinstance(result, str)

    def test_valid_yaml(self):
        compiler = IDDCompiler()
        yaml_str = compiler.compile_to_yaml(_decomposition())
        parsed = yaml.safe_load(yaml_str)
        assert isinstance(parsed, dict)
        assert "steps" in parsed

    def test_yaml_roundtrip_preserves_structure(self):
        compiler = IDDCompiler()
        yaml_str = compiler.compile_to_yaml(_decomposition())
        parsed = yaml.safe_load(yaml_str)
        assert parsed["description"] == "Implement feature X"
        assert len(parsed["steps"]) == 2

    def test_yaml_contains_agent_names(self):
        compiler = IDDCompiler()
        yaml_str = compiler.compile_to_yaml(_decomposition())
        assert "explorer" in yaml_str
        assert "builder" in yaml_str


# ===================================================================
# Edge cases
# ===================================================================


class TestCompilerEdgeCases:
    def test_single_agent(self):
        agents = [AgentAssignment(name="solo", role="all", instruction="do everything")]
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(agents=agents))
        assert len(result["steps"]) == 1
        assert "depends_on" not in result["steps"][0]

    def test_empty_agents_list(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(agents=[]))
        assert result["steps"] == []

    def test_recipe_name_slugified(self):
        compiler = IDDCompiler()
        result = compiler.compile(_decomposition(goal="Add Caching to the API Layer!"))
        name = result["name"]
        assert name.startswith("idd-")
        assert " " not in name
        assert name == name.lower()
