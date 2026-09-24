"""Typed outputs and validation for the optional semantic NLU model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

INTENTS = frozenset({
    "schedule",
    "faculty_availability",
    "faculty_schedule",
    "unknown",
})

ENTITY_ROLES = frozenset({
    "BASE_SECTION",
    "ADDED_SECTION",
    "ADDED_COURSE",
    "EXCLUDED_COURSE",
    "FILTER_SECTION",
    "FILTER_COURSE",
    "FACULTY",
    "DAY",
    "CLASS_TYPE",
    "CREDIT_HOURS",
    "TIME_RANGE",
})


@dataclass(frozen=True)
class EntityPrediction:
    """One role-bearing text span predicted by the NLU model."""

    text: str
    label: str
    start: int
    end: int
    confidence: float

    def __post_init__(self) -> None:
        if self.label not in ENTITY_ROLES:
            raise ValueError(f"Unsupported entity role: {self.label}")
        if self.start < 0 or self.end <= self.start:
            raise ValueError("Entity offsets must describe a non-empty span")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Entity confidence must be between zero and one")


@dataclass(frozen=True)
class NluPrediction:
    """Validated model interpretation before catalog grounding and execution."""

    intent: str
    confidence: float
    entities: tuple[EntityPrediction, ...]
    model_version: str

    def __post_init__(self) -> None:
        if self.intent not in INTENTS:
            raise ValueError(f"Unsupported intent: {self.intent}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Intent confidence must be between zero and one")
        ordered = sorted(self.entities, key=lambda entity: (entity.start, entity.end))
        if list(self.entities) != ordered:
            raise ValueError("Entities must be ordered by source position")

    def as_dict(self) -> dict:
        return asdict(self)


def validate_entity_spans(text: str, entities: Iterable[EntityPrediction]) -> None:
    """Ensure predictions point to the exact source text and never overlap."""
    previous_end = 0
    for entity in entities:
        if entity.end > len(text):
            raise ValueError("Entity span extends beyond the source query")
        if text[entity.start:entity.end] != entity.text:
            raise ValueError("Entity text does not match its source offsets")
        if entity.start < previous_end:
            raise ValueError("Entity spans must not overlap")
        previous_end = entity.end
