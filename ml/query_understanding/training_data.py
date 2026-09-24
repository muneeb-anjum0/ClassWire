"""Token alignment, batches, and model-independent evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch.utils.data import Dataset


def _bio_spans(label_ids: torch.Tensor, slot_labels: list[str]) -> set[tuple[str, int, int]]:
    """Decode strict BIO labels into role and token-boundary tuples."""
    spans: set[tuple[str, int, int]] = set()
    active_role: str | None = None
    active_start = 0
    for index, label_id in enumerate(label_ids.tolist()):
        label = slot_labels[int(label_id)]
        if label == "O" or "-" not in label:
            if active_role is not None:
                spans.add((active_role, active_start, index))
                active_role = None
            continue
        prefix, role = label.split("-", 1)
        if prefix == "B" or role != active_role:
            if active_role is not None:
                spans.add((active_role, active_start, index))
            active_role = role
            active_start = index
    if active_role is not None:
        spans.add((active_role, active_start, len(label_ids)))
    return spans


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
    power: float = 0.5,
) -> torch.Tensor:
    """Return bounded inverse-frequency weights for an encoded label field."""
    if not 0.0 < power <= 1.0:
        raise ValueError("power must be greater than zero and at most one")
    counts = torch.zeros(label_count, dtype=torch.float64)
    for row in dataset.rows:
        values = row[field].reshape(-1)
        if ignore_index is not None:
            values = values[values != ignore_index]
        counts += torch.bincount(values, minlength=label_count).to(torch.float64)
    observed = counts > 0
    weights = torch.zeros(label_count, dtype=torch.float64)
    weights[observed] = (counts[observed].sum() / counts[observed]).pow(power)
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
    entity_true_positive: int = 0
    entity_false_positive: int = 0
    entity_false_negative: int = 0

    def update(
        self,
        intent_predictions: torch.Tensor,
        intent_labels: torch.Tensor,
        slot_predictions: torch.Tensor,
        slot_labels: torch.Tensor,
        outside_id: int,
        label_names: list[str],
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
            expected_spans = _bio_spans(expected, label_names)
            predicted_spans = _bio_spans(predicted, label_names)
            self.entity_true_positive += len(expected_spans & predicted_spans)
            self.entity_false_positive += len(predicted_spans - expected_spans)
            self.entity_false_negative += len(expected_spans - predicted_spans)
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
        entity_precision_denominator = self.entity_true_positive + self.entity_false_positive
        entity_recall_denominator = self.entity_true_positive + self.entity_false_negative
        entity_precision = (
            self.entity_true_positive / entity_precision_denominator
            if entity_precision_denominator else 0.0
        )
        entity_recall = (
            self.entity_true_positive / entity_recall_denominator
            if entity_recall_denominator else 0.0
        )
        entity_f1 = (
            2 * entity_precision * entity_recall / (entity_precision + entity_recall)
            if entity_precision + entity_recall else 0.0
        )
        return {
            "examples": self.rows,
            "intent_accuracy": self.intent_correct / self.rows if self.rows else 0.0,
            "slot_precision": precision,
            "slot_recall": recall,
            "slot_f1": f1,
            "entity_precision_exact_span": entity_precision,
            "entity_recall_exact_span": entity_recall,
            "entity_f1_exact_span": entity_f1,
            "joint_exact_match": self.joint_correct / self.rows if self.rows else 0.0,
        }


def evaluate_model(
    model,
    loader,
    device: torch.device,
    outside_id: int,
    slot_labels: list[str],
) -> dict[str, float | int]:
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
                slot_labels,
            )
    return metrics.as_dict()
