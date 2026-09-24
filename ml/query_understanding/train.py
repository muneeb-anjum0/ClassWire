"""Fine-tune TinyBERT for ClassWire intent and entity prediction."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from transformers import AutoTokenizer, get_linear_schedule_with_warmup

from ml.query_understanding.dataset import read_jsonl
from ml.query_understanding.labels import INTENTS, SLOT_LABELS
from ml.query_understanding.modeling import ClassWireTinyNluModel, save_checkpoint
from ml.query_understanding.training_data import (
    EncodedNluDataset,
    balanced_label_weights,
    evaluate_model,
)
from ml.query_understanding.validate_dataset import validate_records

DEFAULT_MODEL = "google/bert_uncased_L-8_H-256_A-4"


def seed_everything(seed: int, *, use_cuda: bool) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if use_cuda:
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/query_understanding/checkpoints/best"))
    parser.add_argument("--base-model", default=DEFAULT_MODEL)
    parser.add_argument("--epochs", type=int, default=14)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=4e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--patience", type=int, default=4)
    parser.add_argument("--intent-loss-weight", type=float, default=2.0)
    parser.add_argument("--slot-loss-weight", type=float, default=1.2)
    parser.add_argument("--slot-weight-power", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cpu")
    args = parser.parse_args()

    cuda_available = torch.cuda.is_available() if args.device != "cpu" else False
    if args.device == "cuda" and not cuda_available:
        raise RuntimeError("CUDA was requested but is not available")
    selected_device = (
        "cuda" if args.device == "cuda"
        else "cpu" if args.device == "cpu"
        else "cuda" if cuda_available
        else "cpu"
    )
    device = torch.device(selected_device)
    seed_everything(args.seed, use_cuda=device.type == "cuda")
    records = read_jsonl(args.dataset)
    dataset_sha256 = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    dataset_report = validate_records(records)
    train_records = [record for record in records if record["split"] == "train"]
    validation_records = [record for record in records if record["split"] == "validation"]
    intent_labels = list(INTENTS)
    slot_labels = list(SLOT_LABELS)
    intent_to_id = {label: index for index, label in enumerate(intent_labels)}
    slot_to_id = {label: index for index, label in enumerate(slot_labels)}
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    train_dataset = EncodedNluDataset(
        train_records, tokenizer, intent_to_id, slot_to_id, args.max_length
    )
    validation_dataset = EncodedNluDataset(
        validation_records, tokenizer, intent_to_id, slot_to_id, args.max_length
    )
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        generator=generator,
        pin_memory=device.type == "cuda",
    )
    validation_loader = DataLoader(validation_dataset, batch_size=args.batch_size)

    model = ClassWireTinyNluModel(
        args.base_model,
        intent_count=len(intent_labels),
        slot_count=len(slot_labels),
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    total_steps = len(train_loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * args.warmup_ratio),
        num_training_steps=total_steps,
    )
    intent_weights = balanced_label_weights(
        train_dataset, "intent_labels", len(intent_labels)
    ).to(device)
    slot_weights = balanced_label_weights(
        train_dataset,
        "slot_labels",
        len(slot_labels),
        ignore_index=-100,
        power=args.slot_weight_power,
    ).to(device)
    intent_loss = nn.CrossEntropyLoss(weight=intent_weights, label_smoothing=0.02)
    slot_loss = nn.CrossEntropyLoss(
        weight=slot_weights,
        ignore_index=-100,
        label_smoothing=0.02,
    )

    history: list[dict] = []
    best_score = -1.0
    stale_epochs = 0
    started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            intent_labels_tensor = batch["intent_labels"].to(device)
            slot_labels_tensor = batch["slot_labels"].to(device)
            intent_logits, slot_logits = model(input_ids, attention_mask)
            loss = (
                args.intent_loss_weight * intent_loss(intent_logits, intent_labels_tensor)
                + args.slot_loss_weight * slot_loss(
                    slot_logits.reshape(-1, len(slot_labels)), slot_labels_tensor.reshape(-1)
                )
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            running_loss += float(loss.detach())

        metrics = evaluate_model(
            model,
            validation_loader,
            device,
            slot_to_id["O"],
            slot_labels,
            intent_to_id["unknown"],
            validation_dataset.family_names,
        )
        score = (
            1.5 * float(metrics["intent_accuracy"])
            + 0.5 * float(metrics["intent_accuracy_macro_family"])
            + float(metrics["entity_f1_exact_span"])
            + float(metrics["joint_exact_match"])
        )
        epoch_report = {
            "epoch": epoch,
            "train_loss": running_loss / max(len(train_loader), 1),
            **metrics,
        }
        history.append(epoch_report)
        print(json.dumps(epoch_report, sort_keys=True))
        if score > best_score:
            best_score = score
            stale_epochs = 0
            save_checkpoint(
                model,
                args.output,
                intent_labels=intent_labels,
                slot_labels=slot_labels,
                max_length=args.max_length,
                metadata={
                    "seed": args.seed,
                    "dataset_sha256": dataset_sha256,
                    "dataset_report": dataset_report,
                    "best_validation": metrics,
                    "trained_device": device.type,
                },
            )
            tokenizer.save_pretrained(args.output / "tokenizer")
        else:
            stale_epochs += 1
            if stale_epochs >= args.patience:
                break

    report = {
        "base_model": args.base_model,
        "device": device.type,
        "duration_seconds": time.perf_counter() - started,
        "best_score": best_score,
        "intent_class_weights": intent_weights.detach().cpu().tolist(),
        "slot_class_weights": slot_weights.detach().cpu().tolist(),
        "intent_loss_weight": args.intent_loss_weight,
        "slot_loss_weight": args.slot_loss_weight,
        "slot_weight_power": args.slot_weight_power,
        "history": history,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "training_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
