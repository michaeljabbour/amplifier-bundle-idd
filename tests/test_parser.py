"""Tests for the IDD Parser (Layer 1 -> 2 decomposition)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from amplifier_module_tool_idd.grammar import Decomposition
from amplifier_module_tool_idd.parser import IDDParser

from helpers import VALID_DECOMPOSITION_JSON, FakeFailingProvider, FakeProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_providers(response_text: str = "{}") -> dict:
    """Create a single-provider dict for the parser."""
    return {"fake": FakeProvider(response_text)}


def _patched_build_request(self, prompt, available_agents):
    """Replacement for _build_chat_request that returns a simple dict.

    Our FakeProvider.complete() accepts anything as the request arg,
    so we just need to bypass the ChatRequest/ChatMessage dependency.
    """
    return {"prompt": prompt, "agents": available_agents}


# ===================================================================
# Well-formed JSON response (via full parse() with patched request)
# ===================================================================


class TestParserHappyPath:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_returns_decomposition_type(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            ["explorer", "builder"],
        )
        assert isinstance(result, Decomposition)

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_parses_intent(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            ["explorer", "builder"],
        )
        assert result.intent.goal == "Add caching to the API layer"
        assert len(result.intent.success_criteria) == 2
        assert "Response time < 200ms" in result.intent.success_criteria

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_parses_trigger(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            ["explorer"],
        )
        assert result.trigger.activation == "user request"
        assert result.trigger.confirmation == "auto"
        assert "Redis is reachable" in result.trigger.pre_conditions

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_parses_agents(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            ["explorer", "zen-architect", "builder"],
        )
        assert len(result.agents) == 3
        names = [a.name for a in result.agents]
        assert "explorer" in names
        assert "zen-architect" in names
        assert "builder" in names

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_parses_context(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            [],
        )
        assert "Python project" in result.context.auto_detected
        assert "Redis connection string" in result.context.provided
        assert "Current response times" in result.context.to_discover

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_parses_behaviors(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            [],
        )
        behavior_names = [b.name for b in result.behaviors]
        assert "tdd" in behavior_names
        assert "incremental" in behavior_names

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_parses_confidence(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            [],
        )
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_all_five_primitives_populated(self):
        """Every decomposition must have all five primitives non-None."""
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            ["explorer"],
        )
        assert result.intent is not None
        assert result.trigger is not None
        assert result.agents is not None and len(result.agents) > 0
        assert result.context is not None
        assert result.behaviors is not None  # may be empty list, but not None

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_raw_input_preserved(self):
        parser = IDDParser()
        result = await parser.parse(
            "Add caching",
            _make_providers(VALID_DECOMPOSITION_JSON),
            [],
        )
        assert result.raw_input == "Add caching"


# ===================================================================
# Markdown-fenced JSON
# ===================================================================


class TestParserMarkdownFences:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_strips_json_fences(self):
        fenced = f"```json\n{VALID_DECOMPOSITION_JSON}\n```"
        parser = IDDParser()
        result = await parser.parse("test", _make_providers(fenced), [])
        assert result.intent.goal == "Add caching to the API layer"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_strips_plain_fences(self):
        fenced = f"```\n{VALID_DECOMPOSITION_JSON}\n```"
        parser = IDDParser()
        result = await parser.parse("test", _make_providers(fenced), [])
        assert result.intent.goal == "Add caching to the API layer"


# ===================================================================
# Error handling -- malformed / empty / failing
# ===================================================================


class TestParserErrorHandling:
    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_malformed_json_returns_fallback(self):
        parser = IDDParser()
        result = await parser.parse(
            "Do something useful",
            _make_providers("this is not JSON at all"),
            [],
        )
        # Fallback decomposition uses the prompt as the goal
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "Do something useful"
        assert result.confidence == 0.0
        # Fallback always has at least one agent named 'self'
        assert result.agents[0].name == "self"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_empty_response_returns_fallback(self):
        parser = IDDParser()
        result = await parser.parse("Empty test", _make_providers(""), [])
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "Empty test"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_provider_failure_returns_fallback(self):
        parser = IDDParser()
        providers = {"failing": FakeFailingProvider()}
        result = await parser.parse("Failing test", providers, [])
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "Failing test"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_no_providers_returns_fallback(self):
        parser = IDDParser()
        result = await parser.parse("No providers", {}, [])
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "No providers"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_partial_json_fills_defaults(self):
        """JSON with only an intent -- everything else should get defaults."""
        partial = json.dumps({"intent": {"goal": "Partial goal"}})
        parser = IDDParser()
        result = await parser.parse("Partial", _make_providers(partial), [])
        assert result.intent.goal == "Partial goal"
        # Default agent created when none supplied
        assert len(result.agents) >= 1
        assert result.agents[0].name == "self"
        assert result.trigger.activation == "user request"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_agents_empty_list_gets_self(self):
        """Empty agents array should produce a fallback self agent."""
        data = json.dumps(
            {
                "intent": {"goal": "g", "success_criteria": ["ok"]},
                "agents": [],
            }
        )
        parser = IDDParser()
        result = await parser.parse("test", _make_providers(data), [])
        assert len(result.agents) == 1
        assert result.agents[0].name == "self"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_confidence_clamped_to_0_1(self):
        data = json.dumps(
            {
                "intent": {"goal": "g", "success_criteria": []},
                "confidence": 5.0,
            }
        )
        parser = IDDParser()
        result = await parser.parse("test", _make_providers(data), [])
        assert result.confidence <= 1.0

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_confidence_non_numeric_defaults_to_zero(self):
        data = json.dumps(
            {
                "intent": {"goal": "g", "success_criteria": []},
                "confidence": "high",
            }
        )
        parser = IDDParser()
        result = await parser.parse("test", _make_providers(data), [])
        assert result.confidence == 0.0


# ===================================================================
# Internal _parse_response (no LLM dependency)
# ===================================================================


class TestParserParseResponseDirect:
    """Test the JSON-to-Decomposition logic without any LLM/provider dependency."""

    def test_valid_json(self):
        parser = IDDParser()
        result = parser._parse_response(VALID_DECOMPOSITION_JSON, "Add caching")
        assert result.intent.goal == "Add caching to the API layer"
        assert result.confidence == 0.85

    def test_malformed_json(self):
        parser = IDDParser()
        result = parser._parse_response("not json", "fallback prompt")
        assert result.intent.goal == "fallback prompt"
        assert result.confidence == 0.0

    def test_extract_json_strips_fences(self):
        fenced = f"```json\n{VALID_DECOMPOSITION_JSON}\n```"
        cleaned = IDDParser._extract_json(fenced)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "Add caching to the API layer"


# ===================================================================
# System prompt construction
# ===================================================================


class TestParserSystemPrompt:
    def test_system_prompt_includes_agents(self):
        """The system prompt template should list available agents."""
        from amplifier_module_tool_idd.parser import _SYSTEM_PROMPT_TEMPLATE

        agents_str = "explorer, builder, zen-architect"
        rendered = _SYSTEM_PROMPT_TEMPLATE.format(available_agents=agents_str)
        assert "explorer, builder, zen-architect" in rendered

    def test_system_prompt_empty_agents(self):
        from amplifier_module_tool_idd.parser import _SYSTEM_PROMPT_TEMPLATE

        rendered = _SYSTEM_PROMPT_TEMPLATE.format(available_agents="(none)")
        assert "(none)" in rendered

    def test_system_prompt_contains_schema(self):
        """Prompt must include the JSON schema for the five primitives."""
        from amplifier_module_tool_idd.parser import _SYSTEM_PROMPT_TEMPLATE

        rendered = _SYSTEM_PROMPT_TEMPLATE.format(available_agents="x")
        assert '"intent"' in rendered
        assert '"trigger"' in rendered
        assert '"agents"' in rendered
        assert '"context"' in rendered
        assert '"behaviors"' in rendered
        assert '"confidence"' in rendered
