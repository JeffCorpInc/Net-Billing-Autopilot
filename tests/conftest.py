"""Pytest configuration ensuring deterministic mock provider for unit tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def _force_mock_provider_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default unit tests to LLM_PROVIDER=mock so tests stay fast and offline-safe."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_MODEL", "mock-engine")
