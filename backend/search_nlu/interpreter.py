"""Routing policy between deterministic search and optional model inference."""

from __future__ import annotations

from typing import Any

from .runtime import predict_with_optional_model
from .schema import NluPrediction

DEFAULT_CONFIDENCE_THRESHOLD = 0.82
DEFAULT_ENTITY_CONFIDENCE_THRESHOLD = 0.70


def should_consult_model(deterministic_result: dict[str, Any]) -> bool:
    """Use the model only when deterministic interpretation is incomplete."""
    if not deterministic_result.get("recognized"):
        return True
    query_plan = deterministic_result.get("query_plan") or {}
    filters = query_plan.get("filters") or {}
    has_grounded_entity = any(filters.get(name) for name in (
        "sections", "faculty", "courses", "codes", "class_types", "credit_hours",
    ))
    return not has_grounded_entity


def optional_semantic_prediction(
    query: str,
    deterministic_result: dict[str, Any],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    entity_confidence_threshold: float = DEFAULT_ENTITY_CONFIDENCE_THRESHOLD,
) -> NluPrediction | None:
    """Return a confident fallback prediction without changing execution yet."""
    if not should_consult_model(deterministic_result):
        return None
    prediction = predict_with_optional_model(query)
    if prediction is None or prediction.confidence < confidence_threshold:
        return None
    if any(
        entity.confidence < entity_confidence_threshold
        for entity in prediction.entities
    ):
        return None
    return prediction
