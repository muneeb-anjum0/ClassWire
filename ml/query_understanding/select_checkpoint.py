"""Select the strongest validation checkpoint without inspecting test results."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REQUIRED_FILES = (
    "model_state.pt",
    "model_config.json",
    "training_report.json",
    "tokenizer",
)


def validation_score(candidate: Path) -> float:
    report = json.loads((candidate / "training_report.json").read_text(encoding="utf-8"))
    return float(report["best_score"])


def select_checkpoint(candidates: list[Path], output: Path, report_path: Path) -> dict:
    """Copy the strongest validation candidate and return its audit report."""
    missing = {
        str(candidate): [name for name in REQUIRED_FILES if not (candidate / name).exists()]
        for candidate in candidates
    }
    invalid = {candidate: files for candidate, files in missing.items() if files}
    if invalid:
        raise FileNotFoundError(f"Incomplete checkpoint candidates: {invalid}")

    scores = {str(candidate): validation_score(candidate) for candidate in candidates}
    selected = max(candidates, key=validation_score)
    output.mkdir(parents=True, exist_ok=True)
    for source in selected.iterdir():
        destination = output / source.name
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

    report = {
        "selection_basis": "validation_only",
        "selected": str(selected),
        "selected_score": scores[str(selected)],
        "candidate_scores": scores,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = select_checkpoint(args.candidates, args.output, args.report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
