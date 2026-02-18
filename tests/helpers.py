"""Shared test fakes and constants for the IDD bundle test suite.

Importable by test modules as ``from helpers import ...`` (the ``tests``
directory is on ``pythonpath`` via pyproject.toml).
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Fakes -- lightweight stand-ins for amplifier-core objects
# ---------------------------------------------------------------------------


class FakeHookResult:
    """Minimal HookResult compatible with what our hooks return."""

    def __init__(self, action: str = "continue", **kwargs):
        self.action = action
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeHookRegistry:
    """Fake HookRegistry that records registrations and emitted events."""

    def __init__(self):
        self._handlers: dict[str, list[dict]] = {}
        self._emitted: list[dict] = []

    def register(self, event: str, handler, priority: int = 0, name: str | None = None):
        if event not in self._handlers:
            self._handlers[event] = []
        entry = {"handler": handler, "priority": priority, "name": name}
        self._handlers[event].append(entry)

        def unregister():
            self._handlers[event].remove(entry)

        return unregister

    async def emit(self, event: str, data: dict):
        self._emitted.append({"event": event, "data": data})
        for entry in self._handlers.get(event, []):
            await entry["handler"](event, data)
        return FakeHookResult(action="continue")


class FakeProvider:
    """Fake LLM provider that returns configurable responses."""

    def __init__(self, response_text: str = "{}"):
        self.name = "fake-provider"
        self._response_text = response_text
        self._calls: list = []

    def get_info(self):
        return {"name": "fake"}

    async def complete(self, request, **kwargs):
        self._calls.append(request)
        resp = type(
            "FakeResponse",
            (),
            {"content": self._response_text, "model": "fake-model"},
        )()
        return resp


class FakeFailingProvider:
    """Provider that always raises on complete()."""

    name = "failing-provider"

    def get_info(self):
        return {"name": "failing"}

    async def complete(self, request, **kwargs):
        raise RuntimeError("simulated provider failure")


class FakeContextManager:
    """Fake context manager."""

    def __init__(self):
        self._messages: list = []

    async def add_message(self, message):
        self._messages.append(message)

    async def get_messages(self):
        return list(self._messages)

    async def should_compact(self):
        return False

    async def compact(self):
        pass

    async def clear(self):
        self._messages.clear()


class FakeCoordinator:
    """Fake coordinator with capabilities and config."""

    def __init__(self, config: dict | None = None):
        self._capabilities: dict = {}
        self._mounted: dict = {}
        self.config = config or {"agents": {}}
        self.hooks = FakeHookRegistry()

    def register_capability(self, name: str, value):
        self._capabilities[name] = value

    def get_capability(self, name: str):
        return self._capabilities.get(name)

    async def mount(self, mount_point: str, module, name: str | None = None):
        if name:
            if mount_point not in self._mounted:
                self._mounted[mount_point] = {}
            self._mounted[mount_point][name] = module
        else:
            self._mounted[mount_point] = module

    @property
    def session(self):
        return None


# ---------------------------------------------------------------------------
# Canonical LLM-style JSON for a valid decomposition
# ---------------------------------------------------------------------------

VALID_DECOMPOSITION_JSON = """{
  "intent": {
    "goal": "Add caching to the API layer",
    "success_criteria": ["Response time < 200ms", "Cache hit ratio > 80%"],
    "scope_in": ["API endpoints", "Redis cache"],
    "scope_out": ["Database schema changes"],
    "values": ["performance", "simplicity"]
  },
  "trigger": {
    "activation": "user request",
    "pre_conditions": ["Redis is reachable"],
    "confirmation": "auto"
  },
  "agents": [
    {
      "name": "explorer",
      "role": "investigator",
      "instruction": "Map the current API structure"
    },
    {
      "name": "zen-architect",
      "role": "designer",
      "instruction": "Design the caching layer"
    },
    {
      "name": "builder",
      "role": "implementer",
      "instruction": "Implement the caching layer"
    }
  ],
  "context": {
    "auto_detected": ["Python project", "FastAPI framework"],
    "provided": ["Redis connection string"],
    "to_discover": ["Current response times"]
  },
  "behaviors": [
    {"name": "tdd"},
    {"name": "incremental"}
  ],
  "confidence": 0.85
}"""

HUMAN_CONFIRM_JSON = """{
  "intent": {
    "goal": "Delete all user data",
    "success_criteria": ["All user data removed"],
    "scope_in": ["user table"],
    "scope_out": [],
    "values": ["thoroughness"]
  },
  "trigger": {
    "activation": "user request",
    "pre_conditions": [],
    "confirmation": "human"
  },
  "agents": [
    {"name": "self", "role": "executor", "instruction": "Delete user data"}
  ],
  "context": {
    "auto_detected": [],
    "provided": [],
    "to_discover": []
  },
  "behaviors": [],
  "confidence": 0.9
}"""
