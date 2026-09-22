"""Dependency-free structured telemetry for latency and usage diagnostics."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import Counter, defaultdict
from typing import Any

from flask import Flask, g, request

LOGGER = logging.getLogger("classwire.telemetry")
_LOCK = threading.Lock()
_COUNTERS: Counter[str] = Counter()
_DURATIONS: dict[str, list[float]] = defaultdict(list)
_MAX_SAMPLES = 500


def increment(name: str, amount: int = 1) -> None:
    with _LOCK:
        _COUNTERS[name] += amount


def observe(name: str, milliseconds: float) -> None:
    with _LOCK:
        samples = _DURATIONS[name]
        samples.append(round(milliseconds, 2))
        if len(samples) > _MAX_SAMPLES:
            del samples[: len(samples) - _MAX_SAMPLES]


def snapshot() -> dict[str, Any]:
    with _LOCK:
        timings = {}
        for name, samples in _DURATIONS.items():
            ordered = sorted(samples)
            timings[name] = {
                "count": len(ordered),
                "average_ms": round(sum(ordered) / len(ordered), 2) if ordered else 0,
                "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] if ordered else 0,
            }
        return {"counters": dict(_COUNTERS), "timings": timings}


def configure_request_telemetry(app: Flask) -> None:
    @app.before_request
    def start_request_telemetry():
        g.request_started_at = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID", "")[:80] or uuid.uuid4().hex

    @app.after_request
    def finish_request_telemetry(response):
        started = getattr(g, "request_started_at", time.perf_counter())
        duration_ms = (time.perf_counter() - started) * 1000
        route = request.url_rule.rule if request.url_rule else request.path
        metric = f"http.{request.method.lower()}.{route}"
        increment(f"{metric}.status_{response.status_code}")
        observe(metric, duration_ms)
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
        response.headers.setdefault("Server-Timing", f'app;dur={duration_ms:.1f}')
        # Render polls health frequently; count it but do not flood logs or
        # spend paid logging quota on routine liveness traffic.
        if route != "/api/health" or response.status_code >= 400:
            LOGGER.info(json.dumps({
                "event": "http_request",
                "request_id": getattr(g, "request_id", ""),
                "method": request.method,
                "route": route,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "response_bytes": response.calculate_content_length(),
            }, separators=(",", ":")))
        return response
