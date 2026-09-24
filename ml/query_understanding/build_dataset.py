"""Build the deterministic ClassWire NLU corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from ml.query_understanding.dataset import generate_examples, write_jsonl

DATASET_VERSION = "classwire-nlu-v3"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ml/query_understanding/data/classwire_nlu.jsonl"))
    parser.add_argument("--total", type=int, default=18_000)
    parser.add_argument("--seed", type=int, default=41)
    args = parser.parse_args()

    records = generate_examples(total=args.total, seed=args.seed)
    write_jsonl(records, args.output)
    dataset_sha256 = hashlib.sha256(args.output.read_bytes()).hexdigest()
    summary = {
        "dataset_version": DATASET_VERSION,
        "seed": args.seed,
        "sha256": dataset_sha256,
        "records": len(records),
        "intents": Counter(record["intent"] for record in records),
        "splits": Counter(record["split"] for record in records),
        "families": len({record["family"] for record in records}),
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
