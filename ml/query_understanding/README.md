# ClassWire query-understanding model

This directory contains the complete offline pipeline for a compact ClassWire NLU model. It classifies the request and extracts role-bearing spans such as a base section, added course, added section, exclusion, faculty member, day, class type, credit filter, and time range.

The model is a guarded assistant to the deterministic search engine. It does not query the database, invent timetable values, or replace catalog grounding. The existing planner remains authoritative when it confidently understands a request. The optional model is consulted only for ambiguous language, and its output must still pass confidence, schema, and catalog checks.

## Why this design

- `google/bert_uncased_L-8_H-256_A-4` provides stronger language capacity while remaining below the 30 MB INT8 deployment gate.
- One shared encoder serves both intent classification and BIO entity tagging.
- The intent head combines the classification token with masked mean pooling, so decisions use the complete request instead of depending on its opening words.
- Dynamic INT8 ONNX export keeps the production artifact small and CPU-friendly.
- Training dependencies never enter the normal Flask deployment.
- The runtime loads lazily, uses one CPU thread, and safely disables itself when no artifact is installed.
- Synthetic examples are labeled during sentence construction, independently of the production parser.
- Template families are isolated by split, so validation and test phrases are structurally unseen during training.
- Tunable bounded inverse-frequency weights prevent frequent base-section and outside-token labels from drowning out rarer filters and exclusions.
- Structurally different templates teach possessive bindings, section-first course pairs, trailing exclusions, time filters, faculty intent contrasts, and unsupported actions that contain valid catalog names.
- Matched contrast families distinguish teaching schedules from availability requests and unsupported actions from timetable searches.
- Three independently seeded candidates are compared using validation metrics only. The held-out test set remains untouched until final evaluation.
- Checkpoint selection emphasizes intent accuracy, macro accuracy across validation families, exact entity spans, and whole-query correctness.
- An `unknown` prediction discards extracted catalog spans before they can reach the deterministic planner.

## Directory map

| Path | Purpose |
| --- | --- |
| `dataset.py` | Controlled sentence composition and exact character-span labels |
| `build_dataset.py` | Reproducible JSONL corpus generation |
| `validate_dataset.py` | Span, duplication, coverage, and split-leakage checks |
| `modeling.py` | TinyBERT encoder with intent and slot heads |
| `train.py` | Seeded fine-tuning, early stopping, and best-checkpoint output |
| `select_checkpoint.py` | Validation-only selection across independently seeded candidates |
| `evaluate.py` | Held-out intent, slot, and joint exact-match metrics |
| `export_onnx.py` | ONNX export, INT8 quantization, checksums, and runtime package |
| `benchmark.py` | CPU latency, memory, artifact size, and accuracy gates |
| `classwire_nlu_kaggle.ipynb` | Ordered Kaggle execution notebook |

Generated datasets, checkpoints, reports, and intermediate model binaries under this directory are ignored by Git. The reviewed v4 runtime artifact is stored at `backend/search_nlu/artifacts/v1`.

## Kaggle workflow

Create a Kaggle notebook, choose a GPU accelerator, enable Internet access, and run the cells in `classwire_nlu_kaggle.ipynb`. The notebook performs these stages in order:

1. Clone ClassWire and install only the offline training requirements.
2. Confirm CUDA visibility and print package versions.
3. Generate 24,000 deterministic labeled queries.
4. Reject duplicate queries, invalid spans, missing labels, and family leakage.
5. Fine-tune three independently seeded two-head TinyBERT candidates with early stopping.
6. Select the strongest checkpoint using overall and macro-family intent accuracy, exact-span entity F1, and joint metrics.
7. Measure the held-out test split once.
8. Export and dynamically quantize ONNX.
9. Benchmark the exact production runtime on CPU.
10. Package the artifact and reports into one downloadable ZIP file.

The notebook writes `classwire_nlu_delivery.zip` to `/kaggle/working`. Download it from the Kaggle Output pane, then inspect `reports/cpu_benchmark.json`. Never install a package whose top-level `passed` value is `false`.

## Local smoke check

Dataset generation and validation require only Python:

```bash
python -m ml.query_understanding.build_dataset \
  --output /tmp/classwire_nlu.jsonl \
  --total 1800
python -m ml.query_understanding.validate_dataset /tmp/classwire_nlu.jsonl
```

Do not install the training requirements into the production backend environment. Use an isolated environment if you need to train locally.
Full model training is intended for Kaggle. The command defaults to CPU locally and the checked-in notebook opts into Kaggle CUDA explicitly.

## Deployment gate

The benchmark exits unsuccessfully unless all defaults pass:

| Gate | Default requirement |
| --- | ---: |
| Intent accuracy | at least 96% |
| Exact-span entity F1 | at least 94% |
| Whole-query joint exact match | at least 85% |
| Warm CPU p95 latency | at most 50 ms |
| Complete artifact size | at most 30 MB |

These are acceptance gates, not claimed measurements. Actual results are written by the Kaggle run and must be reviewed before enabling the artifact.

The benchmark also records an intent confusion matrix, per-family exact-match rates, and exact-span precision, recall, and F1 for every entity role. A failed run can therefore be improved from concrete evidence instead of lowering a gate blindly.

After a successful run:

1. Extract the ZIP locally.
2. Copy the `artifact` directory to `backend/search_nlu/artifacts/v1`.
3. Install `backend/requirements.txt`, which includes the inference-only runtime.
4. Run the full backend suite and the packaged benchmark again on a CPU-only machine.
5. Pin production to a supported Python 3.13 runtime before enabling ONNX Runtime on Render.
6. Enable semantic fallback only after shadow-mode logs confirm that it improves unresolved queries without regressing deterministic results.

The ordinary `backend/requirements.txt` intentionally remains unchanged until the artifact clears this process.
