"""Tests for the IDD Parser (Layer 1 -> 2 decomposition)."""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest

from amplifier_module_tool_idd.grammar import Decomposition
from amplifier_module_tool_idd.parser import IDDParser, _as_str_list

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


# ===================================================================
# Non-dict JSON — Bug fix: json.loads can return arrays, scalars, etc.
# ===================================================================


class TestParserNonDictJson:
    """json.loads() can return lists, strings, ints, etc. — not just dicts."""

    def test_json_array_returns_fallback(self):
        parser = IDDParser()
        result = parser._parse_response("[1, 2, 3]", "array input")
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "array input"
        assert result.confidence == 0.0

    def test_json_string_returns_fallback(self):
        parser = IDDParser()
        result = parser._parse_response('"just a string"', "string input")
        assert isinstance(result, Decomposition)
        assert result.confidence == 0.0

    def test_json_number_returns_fallback(self):
        parser = IDDParser()
        result = parser._parse_response("42", "number input")
        assert isinstance(result, Decomposition)
        assert result.confidence == 0.0

    def test_json_null_returns_fallback(self):
        parser = IDDParser()
        result = parser._parse_response("null", "null input")
        assert isinstance(result, Decomposition)
        assert result.confidence == 0.0

    def test_json_boolean_returns_fallback(self):
        parser = IDDParser()
        result = parser._parse_response("true", "bool input")
        assert isinstance(result, Decomposition)
        assert result.confidence == 0.0

    def test_non_dict_json_logs_warning(self, caplog):
        parser = IDDParser()
        with caplog.at_level(logging.WARNING, logger="amplifier_module_tool_idd.parser"):
            parser._parse_response("[1, 2]", "array")
        assert any("not an object" in msg for msg in caplog.messages)


# ===================================================================
# Confirmation field validation
# ===================================================================


class TestParserConfirmationValidation:
    """confirmation must be one of 'auto', 'human', 'none'."""

    def test_valid_auto_accepted(self):
        parser = IDDParser()
        data = json.dumps({"trigger": {"confirmation": "auto"}})
        result = parser._parse_response(data, "test")
        assert result.trigger.confirmation == "auto"

    def test_valid_human_accepted(self):
        parser = IDDParser()
        data = json.dumps({"trigger": {"confirmation": "human"}})
        result = parser._parse_response(data, "test")
        assert result.trigger.confirmation == "human"

    def test_valid_none_accepted(self):
        parser = IDDParser()
        data = json.dumps({"trigger": {"confirmation": "none"}})
        result = parser._parse_response(data, "test")
        assert result.trigger.confirmation == "none"

    def test_invalid_confirmation_defaults_to_human(self):
        """Unknown confirmation values fail toward safety (human review)."""
        parser = IDDParser()
        data = json.dumps({"trigger": {"confirmation": "required"}})
        result = parser._parse_response(data, "test")
        assert result.trigger.confirmation == "human"

    def test_invalid_confirmation_yes_defaults_to_human(self):
        """'yes' is not a valid enum value — fail toward human review."""
        parser = IDDParser()
        data = json.dumps({"trigger": {"confirmation": "yes"}})
        result = parser._parse_response(data, "test")
        assert result.trigger.confirmation == "human"

    def test_invalid_confirmation_logs_warning(self, caplog):
        parser = IDDParser()
        data = json.dumps({"trigger": {"confirmation": "required"}})
        with caplog.at_level(logging.WARNING, logger="amplifier_module_tool_idd.parser"):
            parser._parse_response(data, "test")
        assert any("invalid confirmation" in msg for msg in caplog.messages)

    def test_missing_confirmation_defaults_to_auto(self):
        parser = IDDParser()
        data = json.dumps({"trigger": {"activation": "cron"}})
        result = parser._parse_response(data, "test")
        assert result.trigger.confirmation == "auto"


# ===================================================================
# Fallback logging
# ===================================================================


class TestParserFallbackLogging:
    """_fallback_decomposition must log the reason for every invocation."""

    def test_fallback_logs_reason(self, caplog):
        with caplog.at_level(logging.WARNING, logger="amplifier_module_tool_idd.parser"):
            IDDParser._fallback_decomposition("test", reason="test reason")
        assert any("test reason" in msg for msg in caplog.messages)

    def test_fallback_logs_on_malformed_json(self, caplog):
        parser = IDDParser()
        with caplog.at_level(logging.WARNING, logger="amplifier_module_tool_idd.parser"):
            parser._parse_response("not json", "test")
        assert any("fallback" in msg.lower() for msg in caplog.messages)


# ===================================================================
# Empty / whitespace-only prompts
# ===================================================================


class TestParserEmptyPrompt:
    """Edge cases around empty or whitespace-only prompts."""

    def test_empty_prompt_fallback_has_default_goal(self):
        result = IDDParser._fallback_decomposition("", reason="test")
        assert isinstance(result, Decomposition)
        # Goal is empty string (prompt[:200]) — decomposition is still valid
        assert result.intent.goal == ""
        assert result.raw_input == ""

    def test_whitespace_only_prompt(self):
        parser = IDDParser()
        result = parser._parse_response("{}", "   ")
        assert isinstance(result, Decomposition)
        # Goal defaults to the raw_input slice when intent.goal missing
        assert result.intent.goal == "   "

    @pytest.mark.asyncio
    async def test_empty_prompt_via_parse_no_providers(self):
        parser = IDDParser()
        result = await parser.parse("", {}, [])
        assert isinstance(result, Decomposition)
        assert result.confidence == 0.0


# ===================================================================
# Negative confidence clamping
# ===================================================================


class TestParserNegativeConfidence:
    def test_negative_confidence_clamped_to_zero(self):
        parser = IDDParser()
        data = json.dumps(
            {
                "intent": {"goal": "g", "success_criteria": []},
                "confidence": -0.5,
            }
        )
        result = parser._parse_response(data, "test")
        assert result.confidence == 0.0

    def test_large_negative_clamped_to_zero(self):
        parser = IDDParser()
        data = json.dumps(
            {
                "intent": {"goal": "g", "success_criteria": []},
                "confidence": -100.0,
            }
        )
        result = parser._parse_response(data, "test")
        assert result.confidence == 0.0


# ===================================================================
# List-type response.content (content blocks from providers like Anthropic)
# ===================================================================


class _FakeResponse:
    """Response stub with mutable content for content-block tests."""

    def __init__(self, content: object):
        self.content = content
        self.model = "fake-model"


class _ContentBlockProvider:
    """Provider returning a response whose .content is a list of blocks."""

    name = "block-provider"

    def __init__(self, content: object):
        self._content = content

    def get_info(self):
        return {"name": "block"}

    async def complete(self, request, **kwargs):
        return _FakeResponse(self._content)


class TestParserContentBlocks:
    """Provider response.content can be a list of content blocks."""

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_list_content_blocks_with_text_attr(self):
        """Content blocks with .text attribute are joined."""

        class TextBlock:
            def __init__(self, text: str):
                self.text = text

        provider = _ContentBlockProvider([TextBlock(VALID_DECOMPOSITION_JSON)])
        parser = IDDParser()
        result = await parser.parse("test", {"fake": provider}, [])
        assert result.intent.goal == "Add caching to the API layer"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_list_content_blocks_without_text_attr(self):
        """Content blocks without .text fall back to str()."""
        provider = _ContentBlockProvider([VALID_DECOMPOSITION_JSON])
        parser = IDDParser()
        result = await parser.parse("test", {"fake": provider}, [])
        assert result.intent.goal == "Add caching to the API layer"

    @pytest.mark.asyncio
    @patch.object(IDDParser, "_build_chat_request", _patched_build_request)
    async def test_none_content_returns_fallback(self):
        """response.content = None should produce a fallback."""
        provider = _ContentBlockProvider(None)
        parser = IDDParser()
        result = await parser.parse("test", {"fake": provider}, [])
        assert isinstance(result, Decomposition)
        # None → "" via `or ""` → empty string → fallback
        assert result.confidence == 0.0


# ===================================================================
# _as_str_list utility (direct tests)
# ===================================================================


class TestAsStrList:
    """Direct tests for the _as_str_list coercion utility."""

    def test_none_returns_empty(self):
        assert _as_str_list(None) == []

    def test_string_returns_singleton(self):
        assert _as_str_list("hello") == ["hello"]

    def test_empty_string_returns_singleton(self):
        assert _as_str_list("") == [""]

    def test_list_of_strings(self):
        assert _as_str_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_list_with_nones_filtered(self):
        assert _as_str_list(["a", None, "b"]) == ["a", "b"]

    def test_list_with_ints_stringified(self):
        assert _as_str_list([1, 2, 3]) == ["1", "2", "3"]

    def test_list_with_mixed_types(self):
        assert _as_str_list(["a", 1, None, True]) == ["a", "1", "True"]

    def test_empty_list(self):
        assert _as_str_list([]) == []

    def test_int_returns_empty(self):
        assert _as_str_list(42) == []

    def test_dict_returns_empty(self):
        assert _as_str_list({"key": "val"}) == []

    def test_bool_returns_empty(self):
        assert _as_str_list(True) == []


# ===================================================================
# _pick_provider (direct tests)
# ===================================================================


class TestPickProvider:
    def test_returns_first_provider(self):
        p1 = FakeProvider("a")
        p2 = FakeProvider("b")
        result = IDDParser._pick_provider({"first": p1, "second": p2})
        assert result is p1

    def test_empty_dict_returns_none(self):
        assert IDDParser._pick_provider({}) is None

    def test_none_like_empty_returns_none(self):
        # providers could theoretically be falsy
        assert IDDParser._pick_provider({}) is None

    def test_single_provider(self):
        p = FakeProvider("x")
        assert IDDParser._pick_provider({"only": p}) is p


# ===================================================================
# _extract_json edge cases (Bug fixes: fence handling improvements)
# ===================================================================


class TestExtractJsonEdgeCases:
    """Tests for improved _extract_json: uppercase hints, unclosed fences,
    preamble text, and multiple fences."""

    def test_uppercase_json_fence(self):
        """LLMs frequently produce ```JSON instead of ```json."""
        fenced = f"```JSON\n{VALID_DECOMPOSITION_JSON}\n```"
        cleaned = IDDParser._extract_json(fenced)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "Add caching to the API layer"

    def test_jsonl_fence_hint(self):
        """```jsonl hint should be stripped, not leak into content."""
        fenced = '```jsonl\n{"intent": {"goal": "test"}}\n```'
        cleaned = IDDParser._extract_json(fenced)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "test"

    def test_javascript_fence_hint(self):
        """Any language hint should be stripped."""
        fenced = '```javascript\n{"a": 1}\n```'
        cleaned = IDDParser._extract_json(fenced)
        parsed = json.loads(cleaned)
        assert parsed["a"] == 1

    def test_unclosed_fence_recovers_content(self):
        """Streaming truncation leaves an unclosed fence — recover the JSON."""
        unclosed = '```json\n{"intent": {"goal": "truncated"}}'
        cleaned = IDDParser._extract_json(unclosed)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "truncated"

    def test_unclosed_fence_uppercase(self):
        unclosed = '```JSON\n{"a": 1}'
        cleaned = IDDParser._extract_json(unclosed)
        parsed = json.loads(cleaned)
        assert parsed["a"] == 1

    def test_preamble_text_before_json(self):
        """LLMs often add 'Here is the decomposition:' before the JSON."""
        prefixed = 'Here is the decomposition:\n{"intent": {"goal": "test"}}'
        cleaned = IDDParser._extract_json(prefixed)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "test"

    def test_postamble_text_after_json(self):
        """Text after the JSON should be stripped."""
        postfixed = '{"intent": {"goal": "test"}}\nLet me know if you need changes.'
        cleaned = IDDParser._extract_json(postfixed)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "test"

    def test_preamble_and_postamble(self):
        """Text both before and after the JSON."""
        wrapped = 'Sure! Here you go:\n{"a": 1}\nHope that helps!'
        cleaned = IDDParser._extract_json(wrapped)
        parsed = json.loads(cleaned)
        assert parsed["a"] == 1

    def test_multiple_fences_takes_last(self):
        """When LLM shows partial + full output, take the last fence."""
        multi = (
            'Here is the intent:\n```json\n{"partial": true}\n```\n'
            'Here is the full decomposition:\n```json\n{"intent": {"goal": "full"}}\n```'
        )
        cleaned = IDDParser._extract_json(multi)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "full"

    def test_plain_json_no_fences(self):
        """Plain JSON without any fences should pass through."""
        plain = '{"intent": {"goal": "plain"}}'
        cleaned = IDDParser._extract_json(plain)
        parsed = json.loads(cleaned)
        assert parsed["intent"]["goal"] == "plain"

    def test_empty_string(self):
        assert IDDParser._extract_json("") == ""

    def test_whitespace_only(self):
        assert IDDParser._extract_json("   \n  ") == ""

    def test_no_json_at_all(self):
        """Non-JSON text with no braces returns as-is."""
        assert IDDParser._extract_json("just some text") == "just some text"


# ===================================================================
# Non-dict nested primitives (Bug fix: LLM returns strings for sub-objects)
# ===================================================================


class TestNonDictNestedPrimitives:
    """When the LLM returns a string or array where a dict is expected
    (e.g. "intent": "just a string"), the parser must not crash."""

    def test_intent_as_string_uses_defaults(self):
        parser = IDDParser()
        data = json.dumps({"intent": "just summarize it"})
        result = parser._parse_response(data, "test prompt")
        assert isinstance(result, Decomposition)
        # goal falls back to raw_input[:200] since intent_d is now {}
        assert result.intent.goal == "test prompt"

    def test_intent_as_list_uses_defaults(self):
        parser = IDDParser()
        data = json.dumps({"intent": ["goal1", "goal2"]})
        result = parser._parse_response(data, "test")
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "test"

    def test_trigger_as_string_uses_defaults(self):
        parser = IDDParser()
        data = json.dumps({"trigger": "on click"})
        result = parser._parse_response(data, "test")
        assert isinstance(result, Decomposition)
        assert result.trigger.activation == "user request"
        assert result.trigger.confirmation == "auto"

    def test_trigger_as_number_uses_defaults(self):
        parser = IDDParser()
        data = json.dumps({"trigger": 42})
        result = parser._parse_response(data, "test")
        assert isinstance(result, Decomposition)
        assert result.trigger.activation == "user request"

    def test_context_as_string_uses_defaults(self):
        parser = IDDParser()
        data = json.dumps({"context": "the codebase"})
        result = parser._parse_response(data, "test")
        assert isinstance(result, Decomposition)
        assert result.context.auto_detected == []
        assert result.context.provided == []
        assert result.context.to_discover == []

    def test_context_as_list_uses_defaults(self):
        parser = IDDParser()
        data = json.dumps({"context": ["file1.py", "file2.py"]})
        result = parser._parse_response(data, "test")
        assert isinstance(result, Decomposition)
        assert result.context.auto_detected == []

    def test_all_primitives_as_strings(self):
        """Worst case: every sub-object is a string."""
        parser = IDDParser()
        data = json.dumps(
            {
                "intent": "build a thing",
                "trigger": "now",
                "agents": "self",
                "context": "everything",
                "behaviors": "tdd",
                "confidence": 0.5,
            }
        )
        result = parser._parse_response(data, "fallback prompt")
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "fallback prompt"
        assert result.trigger.activation == "user request"
        assert result.context.auto_detected == []
        # agents list: "self" is not iterable as dicts, so empty → fallback self
        assert len(result.agents) == 1
        assert result.agents[0].name == "self"
        assert result.confidence == 0.5


# ===================================================================
# None prompt handling (Bug fix: _fallback_decomposition and
# _dict_to_decomposition must not crash on None)
# ===================================================================


class TestNonePromptHandling:
    """Prompt/raw_input of None must not crash the parser."""

    def test_fallback_with_none_prompt(self):
        result = IDDParser._fallback_decomposition(None, reason="test")  # type: ignore[arg-type]
        assert isinstance(result, Decomposition)
        assert result.intent.goal == ""
        assert result.raw_input == ""

    def test_dict_to_decomposition_with_none_raw_input(self):
        parser = IDDParser()
        result = parser._dict_to_decomposition(
            {"intent": {"goal": "explicit goal"}},
            None,  # type: ignore[arg-type]
        )
        assert isinstance(result, Decomposition)
        assert result.intent.goal == "explicit goal"
        assert result.raw_input == ""

    def test_dict_to_decomposition_none_raw_input_default_goal(self):
        """When intent.goal is missing AND raw_input is None, goal should be ''."""
        parser = IDDParser()
        result = parser._dict_to_decomposition({}, None)  # type: ignore[arg-type]
        assert isinstance(result, Decomposition)
        assert result.intent.goal == ""

    def test_dict_to_decomposition_none_raw_input_agent_instruction(self):
        """Agent instruction falls back to raw_input[:500] — must not crash on None."""
        parser = IDDParser()
        result = parser._dict_to_decomposition({"agents": []}, None)  # type: ignore[arg-type]
        assert isinstance(result, Decomposition)
        assert result.agents[0].instruction == ""


# ===================================================================
# NaN / Inf confidence (Bug fix: non-finite floats must not slip through)
# ===================================================================


class TestNonFiniteConfidence:
    """NaN, inf, and -inf confidence values must be clamped to 0.0."""

    def test_nan_confidence_becomes_zero(self):
        parser = IDDParser()
        # Can't use json.dumps for NaN, so call _dict_to_decomposition directly
        result = parser._dict_to_decomposition(
            {"intent": {"goal": "g", "success_criteria": []}, "confidence": float("nan")},
            "test",
        )
        assert result.confidence == 0.0

    def test_positive_inf_confidence_becomes_zero(self):
        parser = IDDParser()
        result = parser._dict_to_decomposition(
            {"intent": {"goal": "g", "success_criteria": []}, "confidence": float("inf")},
            "test",
        )
        assert result.confidence == 0.0

    def test_negative_inf_confidence_becomes_zero(self):
        parser = IDDParser()
        result = parser._dict_to_decomposition(
            {"intent": {"goal": "g", "success_criteria": []}, "confidence": float("-inf")},
            "test",
        )
        assert result.confidence == 0.0

    def test_normal_float_unaffected(self):
        parser = IDDParser()
        result = parser._dict_to_decomposition(
            {"intent": {"goal": "g", "success_criteria": []}, "confidence": 0.75},
            "test",
        )
        assert result.confidence == 0.75


# ===================================================================
# Nested lists in _as_str_list (Bug fix: flatten instead of repr())
# ===================================================================


class TestAsStrListNested:
    """_as_str_list must flatten nested lists instead of producing repr() strings."""

    def test_nested_lists_flattened(self):
        result = _as_str_list([["fast", "reliable"], ["secure"]])
        assert result == ["fast", "reliable", "secure"]

    def test_mixed_nested_and_flat(self):
        result = _as_str_list(["a", ["b", "c"], "d"])
        assert result == ["a", "b", "c", "d"]

    def test_nested_with_nones_filtered(self):
        result = _as_str_list([["a", None], [None, "b"]])
        assert result == ["a", "b"]

    def test_nested_with_numbers(self):
        result = _as_str_list([[1, 2], [3]])
        assert result == ["1", "2", "3"]

    def test_deeply_nested_not_flattened(self):
        """Only one level of nesting is flattened — deeper nesting uses str()."""
        result = _as_str_list([["a", ["deep"]]])
        # ["deep"] is not itself a list inside the inner list, so str() is used
        assert "a" in result
        assert len(result) == 2  # "a" and "['deep']"
