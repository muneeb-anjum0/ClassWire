"""Acceptance checks for reproducible and leakage-resistant NLU data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.query_understanding.dataset import compose, generate_examples, Mention
from ml.query_understanding.labels import ENTITY_ROLES, INTENTS
from ml.query_understanding.validate_dataset import validate_records


ROOT = Path(__file__).resolve().parents[3]


def test_generated_dataset_has_exact_spans_full_coverage_and_is_reproducible():
    first = generate_examples(total=600, seed=41)
    second = generate_examples(total=600, seed=41)

    report = validate_records(first)

    assert first == second
    assert report["records"] == 600
    assert set(report["intents"]) == set(INTENTS)
    assert set(report["entity_roles"]) == set(ENTITY_ROLES)
    assert report["duplicate_queries"] == 0
    assert report["family_leaks"] == 0


def test_composer_labels_repeated_words_by_position_not_text_search():
    text, entities = compose([
        "Take ", Mention("Networks", "ADDED_COURSE", 1),
        " with ", Mention("BSSE5B", "ADDED_SECTION", 1),
        " but not Networks from my base section",
    ])

    assert text[entities[0]["start"]:entities[0]["end"]] == "Networks"
    assert entities[0]["start"] == 5
    assert entities[1]["group"] == 1


def test_validator_rejects_template_family_leakage():
    records = generate_examples(total=600, seed=41)
    leaked = dict(records[0])
    leaked["id"] = "leaked"
    leaked["text"] += " please"
    leaked["split"] = "test" if records[0]["split"] != "test" else "train"

    with pytest.raises(ValueError, match="leaks across splits"):
        validate_records([*records, leaked])


def test_intent_contrasts_are_isolated_and_catalog_negatives_have_no_entities():
    records = generate_examples(total=1200, seed=73)
    by_family = {record["family"]: record for record in records}

    assert by_family["availability_two_people_semantic_test"]["intent"] == "faculty_availability"
    assert by_family["faculty_schedule_semantic_test"]["intent"] == "faculty_schedule"
    unknown = [
        record for record in records
        if record["family"] == "unknown_catalog_semantic_test"
    ]
    assert unknown
    assert all(record["intent"] == "unknown" and record["entities"] == [] for record in unknown)


def test_kaggle_notebook_contains_every_quality_stage():
    notebook_path = ROOT / "ml" / "query_understanding" / "classwire_nlu_kaggle.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    assert notebook["nbformat"] == 4
    for command in (
        "build_dataset",
        "validate_dataset",
        "query_understanding.train",
        "select_checkpoint",
        "query_understanding.evaluate",
        "export_onnx",
        "query_understanding.benchmark",
        "classwire_nlu_delivery",
    ):
        assert command in source
    assert "--total 24000" in source
    assert "--intent-loss-weight', '2.0" in source
    assert "tinybert-nlu-v4" in source
