"""Small dependency-free concurrent smoke/load test for ClassWire endpoints."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def request_once(url: str, cookie: str | None) -> tuple[int, float]:
    headers = {"Accept-Encoding": "gzip"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(url, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
            return response.status, (time.perf_counter() - started) * 1000
    except Exception:
        return 0, (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5001/api/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--cookie", help="Optional authenticated Cookie header value")
    args = parser.parse_args()
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = [executor.submit(request_once, args.url, args.cookie) for _ in range(max(1, args.requests))]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = time.perf_counter() - started
    latencies = sorted(latency for _, latency in results)
    report = {
        "requests": len(results),
        "concurrency": args.concurrency,
        "successful": sum(1 for status, _ in results if 200 <= status < 400),
        "requests_per_second": round(len(results) / max(elapsed, 0.001), 2),
        "average_ms": round(statistics.fmean(latencies), 2),
        "p95_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 2),
        "max_ms": round(max(latencies), 2),
    }
    print(json.dumps(report, indent=2))
    return 0 if report["successful"] == report["requests"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
