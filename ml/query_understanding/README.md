# ClassWire query-understanding model

This directory contains the complete offline pipeline for a compact ClassWire NLU model. It classifies the request and extracts role-bearing spans such as a base section, added course, added section, exclusion, faculty member, day, class type, credit filter, and time range.

The model is a guarded assistant to the deterministic search engine. It does not query the database, invent timetable values, or replace catalog grounding. The existing planner remains authoritative when it confidently understands a request. The optional model is consulted only for ambiguous language, and its output must still pass confidence, schema, and catalog checks.

## Why this design

- `google/bert_uncased_L-4_H-256_A-4` has four compact encoder layers and remains small enough for an INT8 artifact below the 30 MB deployment gate.
- One shared encoder serves both intent classification and BIO entity tagging.
- Dynamic INT8 ONNX export keeps the production artifact small and CPU-friendly.
- Training dependencies never enter the normal Flask deployment.
- The runtime loads lazily, uses one CPU thread, and safely disables itself when no artifact is installed.
- Synthetic examples are labeled during sentence construction, independently of the production parser.
- Template families are isolated by split, so validation and test phrases are structurally unseen during training.
- Bounded inverse-square-root class weights prevent frequent base-section and outside-token labels from drowning out rarer filters and exclusions.

## Directory map

| Path | Purpose |
| --- | --- |
| `dataset.py` | Controlled sentence composition and exact character-span labels |
| `build_dataset.py` | Reproducible JSONL corpus generation |
| `validate_dataset.py` | Span, duplication, coverage, and split-leakage checks |
| `modeling.py` | TinyBERT encoder with intent and slot heads |
| `train.py` | Seeded fine-tuning, early stopping, and best-checkpoint output |
| `evaluate.py` | Held-out intent, slot, and joint exact-match metrics |
| `export_onnx.py` | ONNX export, INT8 quantization, checksums, and runtime package |
| `benchmark.py` | CPU latency, memory, artifact size, and accuracy gates |
| `classwire_nlu_kaggle.ipynb` | Ordered Kaggle execution notebook |

Generated datasets, checkpoints, reports, and intermediate model binaries under this directory are ignored by Git. Only a reviewed, benchmarked artifact should be copied to the trackable deployment location at `backend/search_nlu/artifacts/v1`.

## Kaggle workflow

Create a Kaggle notebook, choose a GPU accelerator, enable Internet access, and run the cells in `classwire_nlu_kaggle.ipynb`. The notebook performs these stages in order:

1. Clone ClassWire and install only the offline training requirements.
2. Confirm CUDA visibility and print package versions.
3. Generate 12,000 deterministic labeled queries.
4. Reject duplicate queries, invalid spans, missing labels, and family leakage.
5. Fine-tune the two-head TinyBERT model with early stopping.
6. Measure the held-out test split.
7. Export and dynamically quantize ONNX.
8. Benchmark the exact production runtime on CPU.
9. Package the artifact and reports into one downloadable ZIP file.

The notebook writes `classwire_nlu_delivery.zip` to `/kaggle/working`. Download it from the Kaggle Output pane, then inspect `reports/cpu_benchmark.json`. Never install a package whose top-level `passed` value is `false`.

## Local smoke check

Dataset generation and validation require only Python:

```bash
python -m ml.query_understanding.build_dataset \
  --output /tmp/classwire_nlu.jsonl \
  --total 1200
python -m ml.query_understanding.validate_dataset /tmp/classwire_nlu.jsonl
```

Do not install the training requirements into the production backend environment. Use an isolated environment if you need to train locally.

## Deployment gate

The benchmark exits unsuccessfully unless all defaults pass:

| Gate | Default requirement |
| --- | ---: |
| Intent accuracy | at least 94% |
| Exact-span entity F1 | at least 90% |
| Warm CPU p95 latency | at most 50 ms |
| Complete artifact size | at most 30 MB |

These are acceptance gates, not claimed measurements. Actual results are written by the Kaggle run and must be reviewed before enabling the artifact.

The benchmark also records an intent confusion matrix and exact-span precision, recall, and F1 for every entity role. A failed run can therefore be improved from concrete evidence instead of lowering a gate blindly.

After a successful run:

1. Extract the ZIP locally.
2. Copy the `artifact` directory to `backend/search_nlu/artifacts/v1`.
3. Install from `backend/requirements-ml-runtime.txt` in a staging environment.
4. Run the full backend suite and the packaged benchmark again on a CPU-only machine.
5. Pin production to a supported Python 3.13 runtime before enabling ONNX Runtime on Render.
6. Enable semantic fallback only after shadow-mode logs confirm that it improves unresolved queries without regressing deterministic results.

The ordinary `backend/requirements.txt` intentionally remains unchanged until the artifact clears this process.
