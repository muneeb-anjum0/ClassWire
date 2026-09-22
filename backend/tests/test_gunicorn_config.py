"""Production-server configuration regression tests."""

from __future__ import annotations

import runpy
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "gunicorn.conf.py"


def _load_config(monkeypatch, **environment):
    for name in ("PORT", "WEB_CONCURRENCY", "GUNICORN_THREADS"):
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
    assert config["threads"] == 4
    assert config["worker_class"] == "gthread"


def test_invalid_concurrency_values_fall_back_instead_of_breaking_startup(monkeypatch):
    config = _load_config(
        monkeypatch,
        WEB_CONCURRENCY="not-a-number",
        GUNICORN_THREADS="0",
    )

    assert config["workers"] == 1
    assert config["threads"] == 4
