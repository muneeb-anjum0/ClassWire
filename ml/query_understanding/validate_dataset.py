"""Reject malformed labels, leaking template families, and duplicate queries."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from ml.query_understanding.dataset import read_jsonl
from ml.query_understanding.labels import ENTITY_ROLES, INTENTS


def validate_records(records: list[dict]) -> dict:
    errors: list[str] = []
    seen_text: dict[str, str] = {}
    families: dict[str, set[str]] = defaultdict(set)
    role_counts: Counter = Counter()
    intent_counts: Counter = Counter()
    split_counts: Counter = Counter()
    roles_by_split: dict[str, Counter] = defaultdict(Counter)
    intents_by_split: dict[str, Counter] = defaultdict(Counter)

    for index, record in enumerate(records, start=1):
        prefix = f"record {index}"
        text = record.get("text")
        split = record.get("split")
        family = record.get("family")
        intent = record.get("intent")
        entities = record.get("entities")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{prefix}: text must be non-empty")
            continue
        if split not in {"train", "validation", "test"}:
            errors.append(f"{prefix}: invalid split {split!r}")
        if intent not in INTENTS:
            errors.append(f"{prefix}: invalid intent {intent!r}")
        if not isinstance(family, str) or not family:
            errors.append(f"{prefix}: family must be non-empty")
        if not isinstance(entities, list):
            errors.append(f"{prefix}: entities must be a list")
            continue

        normalized = text.casefold()
        if normalized in seen_text:
            errors.append(f"{prefix}: duplicate text also used by {seen_text[normalized]}")
        seen_text[normalized] = record.get("id", prefix)
        families[family].add(split)
        intent_counts[intent] += 1
        intents_by_split[split][intent] += 1
        split_counts[split] += 1

        previous_end = 0
        for entity_index, entity in enumerate(entities, start=1):
            label = entity.get("label")
            start = entity.get("start")
            end = entity.get("end")
            entity_text = entity.get("text")
            entity_prefix = f"{prefix}, entity {entity_index}"
            if label not in ENTITY_ROLES:
                errors.append(f"{entity_prefix}: invalid label {label!r}")
                continue
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
                errors.append(f"{entity_prefix}: invalid offsets")
                continue
            if start < previous_end:
                errors.append(f"{entity_prefix}: entities overlap or are out of order")
            if end > len(text) or text[start:end] != entity_text:
                errors.append(f"{entity_prefix}: span does not match source text")
            previous_end = end
            role_counts[label] += 1
            roles_by_split[split][label] += 1

    for family, splits in families.items():
        if len(splits) > 1:
            errors.append(f"family {family!r} leaks across splits: {sorted(splits)}")
    missing_intents = set(INTENTS) - set(intent_counts)
    missing_roles = set(ENTITY_ROLES) - set(role_counts)
    if missing_intents:
        errors.append(f"missing intents: {sorted(missing_intents)}")
    if missing_roles:
        errors.append(f"missing entity roles: {sorted(missing_roles)}")
    for split in ("train", "validation", "test"):
        split_missing_intents = set(INTENTS) - set(intents_by_split[split])
        split_missing_roles = set(ENTITY_ROLES) - set(roles_by_split[split])
        if split_missing_intents:
            errors.append(f"{split} split is missing intents: {sorted(split_missing_intents)}")
        if split_missing_roles:
            errors.append(f"{split} split is missing entity roles: {sorted(split_missing_roles)}")
    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:30])
        remainder = len(errors) - 30
        if remainder > 0:
            preview += f"\n- ... and {remainder} more"
        raise ValueError(f"Dataset validation failed:\n{preview}")

    return {
        "records": len(records),
        "splits": dict(sorted(split_counts.items())),
        "intents": dict(sorted(intent_counts.items())),
        "entity_roles": dict(sorted(role_counts.items())),
        "entity_roles_by_split": {
            split: dict(sorted(counts.items()))
            for split, counts in sorted(roles_by_split.items())
        },
        "families": len(families),
        "duplicate_queries": 0,
        "family_leaks": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_records(read_jsonl(args.dataset))
    output = json.dumps(report, indent=2, sort_keys=True)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
