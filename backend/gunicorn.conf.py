"""Production Gunicorn settings for Render and equivalent web hosts."""

from __future__ import annotations

import os


def _positive_integer(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


# Render requires the web process to listen on every interface at its assigned
# port. Keeping this in Gunicorn's automatically discovered config also makes a
# dashboard start command such as `gunicorn app:app` safe.
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
# Each worker would own an independent ONNX session and duplicate its weights.
# Keep the 512 MB free instance at one worker unless a larger plan explicitly
# raises CLASSWIRE_MAX_WORKERS. Threads still overlap network-bound Gmail and
# Firestore work without copying the model.
workers = min(
    _positive_integer("WEB_CONCURRENCY", 1),
    _positive_integer("CLASSWIRE_MAX_WORKERS", 1),
)
threads = min(
    _positive_integer("GUNICORN_THREADS", 2),
    _positive_integer("CLASSWIRE_MAX_THREADS", 4),
)
worker_class = "gthread"
preload_app = False

timeout = 90
graceful_timeout = 30
keepalive = 5
max_requests = 500
max_requests_jitter = 50
worker_tmp_dir = "/dev/shm"

# Emit startup and crash details directly into Render's deployment log.
accesslog = "-"
errorlog = "-"
capture_output = True
