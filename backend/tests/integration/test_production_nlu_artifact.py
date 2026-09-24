"""Smoke-test the exact ONNX artifact shipped to Render."""

from __future__ import annotations

import pytest

from search_nlu.runtime import TinyNluRuntime


pytestmark = pytest.mark.integration


def test_production_artifact_executes_the_held_out_availability_contract():
    pytest.importorskip("onnxruntime")
    pytest.importorskip("tokenizers")
    runtime = TinyNluRuntime()

    prediction = runtime.predict(
        "Compare the open hours of Qasim with sir Wahab for Monday"
    )

    assert prediction.intent == "faculty_availability"
    assert prediction.model_version == "tinybert-nlu-v4"
    assert {(entity.label, entity.text) for entity in prediction.entities} == {
        ("FACULTY", "Qasim"),
        ("FACULTY", "sir Wahab"),
        ("DAY", "Monday"),
    }
