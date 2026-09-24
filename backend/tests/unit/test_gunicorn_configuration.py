"""Production-server configuration regression tests."""

from __future__ import annotations

import runpy
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[2] / "gunicorn.conf.py"


def _load_config(monkeypatch, **environment):
    for name in (
        "PORT",
        "WEB_CONCURRENCY",
        "GUNICORN_THREADS",
        "CLASSWIRE_MAX_WORKERS",
        "CLASSWIRE_MAX_THREADS",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    return runpy.run_path(str(CONFIG_PATH))


def test_gunicorn_binds_render_port_on_every_interface(monkeypatch):
    config = _load_config(monkeypatch, PORT="18765")

    assert config["bind"] == "0.0.0.0:18765"


def test_gunicorn_has_safe_free_tier_defaults(monkeypatch):
    config = _load_config(monkeypatch)

    assert config["bind"] == "0.0.0.0:10000"
    assert config["workers"] == 1
    assert config["threads"] == 2
    assert config["worker_class"] == "gthread"
    assert config["preload_app"] is False
    assert config["max_requests"] == 500
    assert config["max_requests_jitter"] == 50


def test_invalid_concurrency_values_fall_back_instead_of_breaking_startup(monkeypatch):
    config = _load_config(
        monkeypatch,
        WEB_CONCURRENCY="not-a-number",
        GUNICORN_THREADS="0",
    )

    assert config["workers"] == 1
    assert config["threads"] == 2


def test_free_tier_caps_accidental_worker_and_thread_overrides(monkeypatch):
    config = _load_config(
        monkeypatch,
        WEB_CONCURRENCY="8",
        GUNICORN_THREADS="12",
    )

    assert config["workers"] == 1
    assert config["threads"] == 4


def test_larger_plans_can_raise_explicit_concurrency_caps(monkeypatch):
    config = _load_config(
        monkeypatch,
        WEB_CONCURRENCY="2",
        GUNICORN_THREADS="8",
        CLASSWIRE_MAX_WORKERS="2",
        CLASSWIRE_MAX_THREADS="6",
    )

    assert config["workers"] == 2
    assert config["threads"] == 6
