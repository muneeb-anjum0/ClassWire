"""Lazy ONNX runtime for the optional TinyBERT query-understanding model."""

from __future__ import annotations

import hashlib
import json
import math
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from .schema import ENTITY_ROLES, INTENTS, EntityPrediction, NluPrediction, validate_entity_spans

DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts" / "v1"
REQUIRED_ARTIFACTS = (
    "classwire_nlu.int8.onnx",
    "tokenizer.json",
    "intent_labels.json",
    "slot_labels.json",
    "metadata.json",
)


def _softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    maximum = max(values)
    exponentials = [math.exp(value - maximum) for value in values]
    total = sum(exponentials)
    return [value / total for value in exponentials]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_labels(intent_labels: list[str], slot_labels: list[str]) -> None:
    if set(intent_labels) != INTENTS or len(intent_labels) != len(INTENTS):
        raise RuntimeError("Tiny NLU intent labels do not match the runtime contract")
    if not slot_labels or slot_labels[0] != "O" or len(slot_labels) != 1 + 2 * len(ENTITY_ROLES):
        raise RuntimeError("Tiny NLU slot labels do not match the runtime contract")
    expected_slots = {"O"} | {
        f"{prefix}-{role}"
        for role in ENTITY_ROLES
        for prefix in ("B", "I")
    }
    if set(slot_labels) != expected_slots:
        raise RuntimeError("Tiny NLU slot labels do not match the runtime contract")


class TinyNluRuntime:
    """Load one quantized model on demand and share it across requests."""

    def __init__(self, artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR) -> None:
        self.artifact_dir = Path(artifact_dir)
        self._lock = threading.Lock()
        self._session: Any | None = None
        self._tokenizer: Any | None = None
        self._intent_labels: list[str] = []
        self._slot_labels: list[str] = []
        self._metadata: dict[str, Any] = {}

    @property
    def available(self) -> bool:
        return all((self.artifact_dir / name).is_file() for name in REQUIRED_ARTIFACTS)

    @property
    def loaded(self) -> bool:
        return self._session is not None

    def load(self) -> None:
        if self.loaded:
            return
        if not self.available:
            missing = [
                name for name in REQUIRED_ARTIFACTS
                if not (self.artifact_dir / name).is_file()
            ]
            raise FileNotFoundError(f"Tiny NLU artifacts are incomplete: {', '.join(missing)}")

        with self._lock:
            if self.loaded:
                return
            metadata = json.loads(
                (self.artifact_dir / "metadata.json").read_text(encoding="utf-8")
            )
            intent_labels = json.loads(
                (self.artifact_dir / "intent_labels.json").read_text(encoding="utf-8")
            )
            slot_labels = json.loads(
                (self.artifact_dir / "slot_labels.json").read_text(encoding="utf-8")
            )
            _validate_labels(intent_labels, slot_labels)
            expected_digest = metadata.get("model_sha256")
            model_path = self.artifact_dir / "classwire_nlu.int8.onnx"
            if not isinstance(expected_digest, str) or _sha256(model_path) != expected_digest:
                raise RuntimeError("Tiny NLU model checksum does not match metadata")
            max_length = int(metadata.get("max_length", 0))
            if not 1 <= max_length <= 256:
                raise RuntimeError("Tiny NLU max length is outside the runtime limit")
            try:
                import onnxruntime as ort
                from tokenizers import Tokenizer
            except ImportError as error:
                raise RuntimeError(
                    "Tiny NLU runtime requires onnxruntime and tokenizers"
                ) from error

            self._metadata = metadata
            self._intent_labels = intent_labels
            self._slot_labels = slot_labels
            tokenizer = Tokenizer.from_file(str(self.artifact_dir / "tokenizer.json"))
            tokenizer.enable_truncation(max_length=max_length)
            tokenizer.enable_padding(
                length=max_length,
                pad_id=tokenizer.token_to_id("[PAD]") or 0,
                pad_token="[PAD]",
            )

            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session = ort.InferenceSession(
                str(model_path),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            self._tokenizer = tokenizer
            self._session = session

    def predict(self, query: str) -> NluPrediction:
        if not query.strip():
            raise ValueError("A non-empty query is required")
        self.load()

        import numpy as np

        encoding = self._tokenizer.encode(query)
        input_ids = np.asarray([encoding.ids], dtype=np.int64)
        attention_mask = np.asarray([encoding.attention_mask], dtype=np.int64)
        intent_logits, slot_logits = self._session.run(
            ["intent_logits", "slot_logits"],
            {"input_ids": input_ids, "attention_mask": attention_mask},
        )

        intent_probabilities = _softmax(intent_logits[0].tolist())
        intent_index = max(range(len(intent_probabilities)), key=intent_probabilities.__getitem__)
        token_probabilities = [_softmax(values.tolist()) for values in slot_logits[0]]
        token_labels = [
            max(range(len(probabilities)), key=probabilities.__getitem__)
            for probabilities in token_probabilities
        ]
        entities = self._decode_entities(
            query,
            encoding.offsets,
            encoding.attention_mask,
            token_labels,
            token_probabilities,
        )
        prediction = NluPrediction(
            intent=self._intent_labels[intent_index],
            confidence=float(intent_probabilities[intent_index]),
            entities=tuple(entities),
            model_version=str(self._metadata.get("model_version", "unknown")),
        )
        validate_entity_spans(query, prediction.entities)
        return prediction

    def _decode_entities(
        self,
        query: str,
        offsets: list[tuple[int, int]],
        attention_mask: list[int],
        token_labels: list[int],
        token_probabilities: list[list[float]],
    ) -> list[EntityPrediction]:
        groups: list[dict[str, Any]] = []
        for offset, active, label_index, probabilities in zip(
            offsets,
            attention_mask,
            token_labels,
            token_probabilities,
        ):
            start, end = offset
            if not active or start == end:
                continue
            label = self._slot_labels[label_index]
            if label == "O" or "-" not in label:
                continue
            prefix, role = label.split("-", 1)
            confidence = float(probabilities[label_index])
            can_extend = bool(
                groups
                and prefix == "I"
                and groups[-1]["label"] == role
                and start <= groups[-1]["end"] + 1
            )
            if can_extend:
                groups[-1]["end"] = end
                groups[-1]["confidences"].append(confidence)
            else:
                groups.append({
                    "label": role,
                    "start": start,
                    "end": end,
                    "confidences": [confidence],
                })

        return [
            EntityPrediction(
                text=query[group["start"]:group["end"]],
                label=group["label"],
                start=group["start"],
                end=group["end"],
                confidence=sum(group["confidences"]) / len(group["confidences"]),
            )
            for group in groups
        ]


@lru_cache(maxsize=2)
def get_runtime(artifact_dir: str = str(DEFAULT_ARTIFACT_DIR)) -> TinyNluRuntime:
    return TinyNluRuntime(artifact_dir)


def predict_with_optional_model(
    query: str,
    artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR,
) -> NluPrediction | None:
    """Return no prediction when the optional model has not been installed."""
    runtime = get_runtime(str(Path(artifact_dir)))
    if not runtime.available:
        return None
    return runtime.predict(query)
