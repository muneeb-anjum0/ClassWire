"""Evaluate a saved checkpoint against a held-out dataset split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

from ml.query_understanding.dataset import read_jsonl
from ml.query_understanding.modeling import load_checkpoint
from ml.query_understanding.training_data import EncodedNluDataset, evaluate_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--output", type=Path, default=Path("ml/query_understanding/reports/evaluation.json"))
    args = parser.parse_args()

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    selected_device = (
        "cuda" if args.device == "cuda"
        else "cpu" if args.device == "cpu"
        else "cuda" if torch.cuda.is_available()
        else "cpu"
    )
    device = torch.device(selected_device)
    model, config = load_checkpoint(args.checkpoint, device)
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint / "tokenizer", use_fast=True)
    intent_to_id = {label: index for index, label in enumerate(config["intent_labels"])}
    slot_to_id = {label: index for index, label in enumerate(config["slot_labels"])}
    records = [record for record in read_jsonl(args.dataset) if record["split"] == args.split]
    dataset = EncodedNluDataset(
        records, tokenizer, intent_to_id, slot_to_id, int(config["max_length"])
    )
    metrics = evaluate_model(
        model, DataLoader(dataset, batch_size=args.batch_size), device, slot_to_id["O"]
    )
    report = {
        "split": args.split,
        "checkpoint": str(args.checkpoint),
        "device": device.type,
        **metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
