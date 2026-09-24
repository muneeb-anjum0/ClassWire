"""Tests for validation-only NLU checkpoint selection."""

from __future__ import annotations

import json

from ml.query_understanding.select_checkpoint import REQUIRED_FILES, select_checkpoint


def _candidate(path, score: float) -> None:
    path.mkdir()
    (path / "model_state.pt").write_bytes(b"model")
    (path / "model_config.json").write_text("{}", encoding="utf-8")
    (path / "training_report.json").write_text(
        json.dumps({"best_score": score}), encoding="utf-8"
    )
    (path / "tokenizer").mkdir()


def test_checkpoint_selection_uses_validation_score_and_records_every_candidate(tmp_path):
    weaker = tmp_path / "candidate-41"
    stronger = tmp_path / "candidate-73"
    _candidate(weaker, 2.71)
    _candidate(stronger, 2.84)
    output = tmp_path / "best"
    report_path = tmp_path / "selection.json"

    report = select_checkpoint([weaker, stronger], output, report_path)

    assert report["selection_basis"] == "validation_only"
    assert report["selected"] == str(stronger)
    assert report["selected_score"] == 2.84
    assert set(report["candidate_scores"]) == {str(weaker), str(stronger)}
    assert all((output / name).exists() for name in REQUIRED_FILES)
    assert json.loads(report_path.read_text(encoding="utf-8")) == report
