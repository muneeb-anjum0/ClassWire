"""Verify the packaged NLU artifact in a fresh production-like process."""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.search_nlu.runtime import TinyNluRuntime


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-peak-rss-mib", type=float, default=460.0)
    args = parser.parse_args()

    runtime = TinyNluRuntime()
    started = time.perf_counter()
    prediction = runtime.predict(
        "Compare the open hours of Qasim with sir Wahab for Monday"
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    entities = {(entity.label, entity.text) for entity in prediction.entities}
    expected = {
        ("FACULTY", "Qasim"),
        ("FACULTY", "sir Wahab"),
        ("DAY", "Monday"),
    }
    report = {
        "available": runtime.available,
        "loaded": runtime.loaded,
        "model_version": prediction.model_version,
        "intent": prediction.intent,
        "entities_match": entities == expected,
        "cold_prediction_ms": round(elapsed_ms, 2),
        "peak_rss_mib": round(peak_rss_mib, 2),
        "peak_rss_limit_mib": args.max_peak_rss_mib,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if prediction.intent != "faculty_availability" or entities != expected:
        raise SystemExit("Production NLU smoke query failed")
    if peak_rss_mib > args.max_peak_rss_mib:
        raise SystemExit("Production NLU process exceeded its memory gate")


if __name__ == "__main__":
    main()
