"""Pytest configuration ensuring deterministic offline analyzer is used during unit tests."""
import os
import pytest


@pytest.fixture(autouse=True)
def default_offline_for_tests(monkeypatch):
    """Ensure automated tests use deterministic offline analyzer by default to protect API quotas."""
    monkeypatch.setenv("OPENAI_MODEL", "offline-fallback-v1")

