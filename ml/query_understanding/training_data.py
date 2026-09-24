"""Token alignment, batches, and model-independent evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch.utils.data import Dataset


def align_slot_labels(offsets: list[tuple[int, int]], entities: list[dict], slot_to_id: dict[str, int]) -> list[int]:
    labels: list[int] = []
    for token_start, token_end in offsets:
        if token_start == token_end:
            labels.append(-100)
            continue
        matched = None
        for entity in entities:
            if token_start < entity["end"] and token_end > entity["start"]:
                matched = entity
                break
        if matched is None:
            labels.append(slot_to_id["O"])
            continue
        prefix = "B" if token_start <= matched["start"] else "I"
        labels.append(slot_to_id[f"{prefix}-{matched['label']}"])
    return labels


class EncodedNluDataset(Dataset):
    def __init__(
        self,
        records: list[dict],
        tokenizer,
        intent_to_id: dict[str, int],
        slot_to_id: dict[str, int],
        max_length: int,
    ) -> None:
        self.rows: list[dict[str, torch.Tensor]] = []
        for record in records:
            encoded = tokenizer(
                record["text"],
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_offsets_mapping=True,
            )
            slot_labels = align_slot_labels(encoded.pop("offset_mapping"), record["entities"], slot_to_id)
            self.rows.append({
                "input_ids": torch.tensor(encoded["input_ids"], dtype=torch.long),
                "attention_mask": torch.tensor(encoded["attention_mask"], dtype=torch.long),
                "intent_labels": torch.tensor(intent_to_id[record["intent"]], dtype=torch.long),
                "slot_labels": torch.tensor(slot_labels, dtype=torch.long),
            })

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        return self.rows[index]


def balanced_label_weights(
    dataset: EncodedNluDataset,
    field: str,
    label_count: int,
    *,
    ignore_index: int | None = None,
    maximum: float = 5.0,
) -> torch.Tensor:
    """Return bounded inverse-square-root weights for an encoded label field."""
    counts = torch.zeros(label_count, dtype=torch.float64)
    for row in dataset.rows:
        values = row[field].reshape(-1)
        if ignore_index is not None:
            values = values[values != ignore_index]
        counts += torch.bincount(values, minlength=label_count).to(torch.float64)
    observed = counts > 0
    weights = torch.zeros(label_count, dtype=torch.float64)
    weights[observed] = torch.sqrt(counts[observed].sum() / counts[observed])
    weights[observed] /= weights[observed].mean()
    weights[observed] = weights[observed].clamp(min=0.25, max=maximum)
    return weights.to(torch.float32)


@dataclass
class MetricAccumulator:
    intent_correct: int = 0
    rows: int = 0
    joint_correct: int = 0
    slot_true_positive: int = 0
    slot_false_positive: int = 0
    slot_false_negative: int = 0

    def update(
        self,
        intent_predictions: torch.Tensor,
        intent_labels: torch.Tensor,
        slot_predictions: torch.Tensor,
        slot_labels: torch.Tensor,
        outside_id: int,
    ) -> None:
        for intent_prediction, intent_label, slot_prediction, slot_label in zip(
            intent_predictions.cpu(),
            intent_labels.cpu(),
            slot_predictions.cpu(),
            slot_labels.cpu(),
        ):
            intent_match = int(intent_prediction) == int(intent_label)
            self.intent_correct += int(intent_match)
            self.rows += 1
            valid = slot_label != -100
            expected = slot_label[valid]
            predicted = slot_prediction[valid]
            self.joint_correct += int(intent_match and torch.equal(expected, predicted))
            expected_entity = expected != outside_id
            predicted_entity = predicted != outside_id
            self.slot_true_positive += int(((expected == predicted) & expected_entity).sum())
            self.slot_false_positive += int((predicted_entity & (predicted != expected)).sum())
            self.slot_false_negative += int((expected_entity & (predicted != expected)).sum())

    def as_dict(self) -> dict[str, float | int]:
        precision_denominator = self.slot_true_positive + self.slot_false_positive
        recall_denominator = self.slot_true_positive + self.slot_false_negative
        precision = self.slot_true_positive / precision_denominator if precision_denominator else 0.0
        recall = self.slot_true_positive / recall_denominator if recall_denominator else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            "examples": self.rows,
            "intent_accuracy": self.intent_correct / self.rows if self.rows else 0.0,
            "slot_precision": precision,
            "slot_recall": recall,
            "slot_f1": f1,
            "joint_exact_match": self.joint_correct / self.rows if self.rows else 0.0,
        }


def evaluate_model(model, loader, device: torch.device, outside_id: int) -> dict[str, float | int]:
    metrics = MetricAccumulator()
    model.eval()
    with torch.inference_mode():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            intent_logits, slot_logits = model(input_ids, attention_mask)
            metrics.update(
                intent_logits.argmax(dim=-1),
                batch["intent_labels"],
                slot_logits.argmax(dim=-1),
                batch["slot_labels"],
                outside_id,
            )
    return metrics.as_dict()
