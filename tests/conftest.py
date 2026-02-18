"""Pytest configuration and shared fixtures for the IDD bundle test suite."""

from __future__ import annotations

import pytest

from helpers import (
    FakeContextManager,
    FakeCoordinator,
    FakeHookRegistry,
    FakeProvider,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_coordinator():
    return FakeCoordinator(config={"agents": {"explorer": {}, "zen-architect": {}, "builder": {}}})


@pytest.fixture
def fake_hooks():
    return FakeHookRegistry()


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def fake_context():
    return FakeContextManager()
