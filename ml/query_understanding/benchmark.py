"""Measure held-out accuracy, CPU latency, memory, and artifact size."""

from __future__ import annotations

import argparse
import json
import resource
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from backend.search_nlu.runtime import TinyNluRuntime
from ml.query_understanding.dataset import read_jsonl


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return ordered[index]


def entity_key(entity: dict) -> tuple[str, int, int]:
    return entity["label"], int(entity["start"]), int(entity["end"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--split", default="test", choices=("validation", "test"))
    parser.add_argument("--runs", type=int, default=2_000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("ml/query_understanding/reports/benchmark.json"))
    parser.add_argument("--min-intent-accuracy", type=float, default=0.94)
    parser.add_argument("--min-entity-f1", type=float, default=0.90)
    parser.add_argument("--max-p95-ms", type=float, default=50.0)
    parser.add_argument("--max-artifact-mb", type=float, default=30.0)
    args = parser.parse_args()

    records = [record for record in read_jsonl(args.dataset) if record["split"] == args.split]
    if not records:
        raise ValueError(f"No records found for split {args.split}")
    runtime = TinyNluRuntime(args.artifact)
    load_started = time.perf_counter()
    runtime.load()
    load_ms = (time.perf_counter() - load_started) * 1000

    intent_correct = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    joint_correct = 0
    intent_confusion: Counter = Counter()
    role_counts: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        prediction = runtime.predict(record["text"])
        intent_match = prediction.intent == record["intent"]
        intent_correct += int(intent_match)
        intent_confusion[(record["intent"], prediction.intent)] += 1
        expected = {entity_key(entity) for entity in record["entities"]}
        predicted = {
            (entity.label, entity.start, entity.end)
            for entity in prediction.entities
        }
        true_positive += len(expected & predicted)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)
        for role, _, _ in expected & predicted:
            role_counts[role]["true_positive"] += 1
        for role, _, _ in predicted - expected:
            role_counts[role]["false_positive"] += 1
        for role, _, _ in expected - predicted:
            role_counts[role]["false_negative"] += 1
        joint_correct += int(intent_match and expected == predicted)

    for index in range(args.warmup):
        runtime.predict(records[index % len(records)]["text"])
    latencies: list[float] = []
    for index in range(args.runs):
        started = time.perf_counter()
        runtime.predict(records[index % len(records)]["text"])
        latencies.append((time.perf_counter() - started) * 1000)

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    entity_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    artifact_bytes = sum(path.stat().st_size for path in args.artifact.iterdir() if path.is_file())
    per_role = {}
    for role, counts in sorted(role_counts.items()):
        role_tp = counts["true_positive"]
        role_fp = counts["false_positive"]
        role_fn = counts["false_negative"]
        role_precision = role_tp / (role_tp + role_fp) if role_tp + role_fp else 0.0
        role_recall = role_tp / (role_tp + role_fn) if role_tp + role_fn else 0.0
        role_f1 = (
            2 * role_precision * role_recall / (role_precision + role_recall)
            if role_precision + role_recall else 0.0
        )
        per_role[role] = {
            "precision": role_precision,
            "recall": role_recall,
            "f1": role_f1,
            **dict(counts),
        }
    report = {
        "split": args.split,
        "examples": len(records),
        "intent_accuracy": intent_correct / len(records),
        "entity_precision_exact_span": precision,
        "entity_recall_exact_span": recall,
        "entity_f1_exact_span": entity_f1,
        "joint_exact_match": joint_correct / len(records),
        "cold_load_ms": load_ms,
        "latency_mean_ms": statistics.fmean(latencies),
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "latency_p99_ms": percentile(latencies, 0.99),
        "runs": len(latencies),
        "artifact_bytes": artifact_bytes,
        "artifact_megabytes": artifact_bytes / (1024 * 1024),
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "intent_confusion": {
            f"{expected} -> {predicted}": count
            for (expected, predicted), count in sorted(intent_confusion.items())
        },
        "entity_metrics_by_role": per_role,
    }
    gates = {
        "intent_accuracy": report["intent_accuracy"] >= args.min_intent_accuracy,
        "entity_f1": report["entity_f1_exact_span"] >= args.min_entity_f1,
        "p95_latency": report["latency_p95_ms"] <= args.max_p95_ms,
        "artifact_size": report["artifact_megabytes"] <= args.max_artifact_mb,
    }
    report["quality_gates"] = gates
    report["passed"] = all(gates.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
