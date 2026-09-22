"""Shared collection policy for the ClassWire backend quality suite."""

from pathlib import Path

import pytest


SUITE_MARKERS = ("unit", "integration", "acceptance")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Label each test from its suite directory for targeted local runs."""
    for item in items:
        path_parts = Path(str(item.path)).parts
        marker = next((name for name in SUITE_MARKERS if name in path_parts), None)
        if marker:
            item.add_marker(getattr(pytest.mark, marker))
