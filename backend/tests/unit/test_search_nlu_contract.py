"""Contract tests for optional semantic query understanding."""

from __future__ import annotations

import hashlib
import json

import pytest

from search_nlu.interpreter import optional_semantic_prediction, should_consult_model
from search_nlu.runtime import TinyNluRuntime, predict_with_optional_model
from search_nlu.schema import EntityPrediction, NluPrediction, validate_entity_spans
from search_nlu.schema import ENTITY_ROLES, INTENTS


def test_prediction_schema_accepts_ordered_exact_spans():
    query = "Show BSSE7A on Monday"
    entities = (
        EntityPrediction("BSSE7A", "BASE_SECTION", 5, 11, 0.98),
        EntityPrediction("Monday", "DAY", 15, 21, 0.96),
    )
    prediction = NluPrediction("schedule", 0.99, entities, "test-v1")

    validate_entity_spans(query, prediction.entities)

    assert prediction.as_dict()["entities"][0]["label"] == "BASE_SECTION"


@pytest.mark.parametrize(
    "entity",
    [
        EntityPrediction("BSSE7A", "BASE_SECTION", 5, 11, 0.98),
        EntityPrediction("Monday", "DAY", 15, 21, 0.96),
    ],
)
def test_prediction_schema_rejects_spans_that_do_not_match_source(entity):
    with pytest.raises(ValueError):
        validate_entity_spans("different source", (entity,))


def test_optional_runtime_is_safe_when_no_artifact_exists(tmp_path):
    runtime = TinyNluRuntime(tmp_path)

    assert runtime.available is False
    assert runtime.loaded is False
    assert predict_with_optional_model("show BSSE7A", tmp_path) is None


def test_runtime_rejects_a_model_with_a_mismatched_checksum(tmp_path):
    model = tmp_path / "classwire_nlu.int8.onnx"
    model.write_bytes(b"not an onnx model")
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    (tmp_path / "intent_labels.json").write_text(
        json.dumps(sorted(INTENTS)), encoding="utf-8"
    )
    slots = ["O"] + [
        f"{prefix}-{role}"
        for role in sorted(ENTITY_ROLES)
        for prefix in ("B", "I")
    ]
    (tmp_path / "slot_labels.json").write_text(json.dumps(slots), encoding="utf-8")
    (tmp_path / "metadata.json").write_text(
        json.dumps({"model_sha256": "0" * 64, "max_length": 96}),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="checksum"):
        TinyNluRuntime(tmp_path).load()


def test_runtime_accepts_the_checksum_before_loading_optional_dependencies(tmp_path, monkeypatch):
    model = tmp_path / "classwire_nlu.int8.onnx"
    model.write_bytes(b"model bytes")
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    (tmp_path / "intent_labels.json").write_text(
        json.dumps(sorted(INTENTS)), encoding="utf-8"
    )
    slots = ["O"] + [
        f"{prefix}-{role}"
        for role in sorted(ENTITY_ROLES)
        for prefix in ("B", "I")
    ]
    (tmp_path / "slot_labels.json").write_text(json.dumps(slots), encoding="utf-8")
    (tmp_path / "metadata.json").write_text(
        json.dumps({
            "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            "max_length": 96,
        }),
        encoding="utf-8",
    )
    real_import = __import__

    def reject_optional_runtime(name, *args, **kwargs):
        if name in {"onnxruntime", "tokenizers"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", reject_optional_runtime)

    with pytest.raises(RuntimeError, match="requires onnxruntime and tokenizers"):
        TinyNluRuntime(tmp_path).load()


def test_model_is_consulted_only_for_unresolved_interpretations():
    assert should_consult_model({"recognized": False}) is True
    assert should_consult_model({
        "recognized": True,
        "query_plan": {"filters": {"sections": ["BS(SE)-7A"]}},
    }) is False
    assert should_consult_model({
        "recognized": True,
        "query_plan": {"filters": {}},
    }) is True


def test_low_confidence_semantic_prediction_is_not_returned(monkeypatch):
    low_confidence = NluPrediction("schedule", 0.40, (), "test-v1")
    monkeypatch.setattr(
        "search_nlu.interpreter.predict_with_optional_model",
        lambda query: low_confidence,
    )

    assert optional_semantic_prediction("something vague", {"recognized": False}) is None
