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
workers = _positive_integer("WEB_CONCURRENCY", 1)
threads = _positive_integer("GUNICORN_THREADS", 4)
worker_class = "gthread"

timeout = 90
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
worker_tmp_dir = "/dev/shm"

# Emit startup and crash details directly into Render's deployment log.
accesslog = "-"
errorlog = "-"
capture_output = True
