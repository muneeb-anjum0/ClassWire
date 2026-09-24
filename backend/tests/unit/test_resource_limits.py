"""Free-tier resource budget regression tests."""

from __future__ import annotations

from core.resource_limits import positive_int_env, process_memory_snapshot


def test_positive_integer_environment_values_are_bounded(monkeypatch):
    monkeypatch.setenv("CLASSWIRE_TEST_LIMIT", "999")

    assert positive_int_env("CLASSWIRE_TEST_LIMIT", 24, maximum=128) == 128


def test_invalid_resource_limit_uses_the_safe_default(monkeypatch):
    monkeypatch.setenv("CLASSWIRE_TEST_LIMIT", "invalid")

    assert positive_int_env("CLASSWIRE_TEST_LIMIT", 24, maximum=128) == 24


def test_process_memory_snapshot_has_a_stable_dependency_free_contract():
    snapshot = process_memory_snapshot()

    assert set(snapshot) == {
        "rss_mib",
        "peak_rss_mib",
        "cgroup_used_mib",
        "cgroup_limit_mib",
        "cgroup_headroom_mib",
    }
    assert snapshot["rss_mib"] is None or snapshot["rss_mib"] > 0
