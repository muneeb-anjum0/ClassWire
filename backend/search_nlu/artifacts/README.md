# NLU deployment artifacts

This directory is empty until a Kaggle-trained model clears every documented quality gate.

A deployable version directory must contain exactly these runtime files:

```text
v1/
├── classwire_nlu.int8.onnx
├── intent_labels.json
├── metadata.json
├── slot_labels.json
└── tokenizer.json
```

Before adding a version:

1. Confirm the packaged test evaluation and CPU benchmark passed.
2. Confirm `metadata.json` contains the expected model version and ONNX SHA-256 digest.
3. Run the benchmark again against the extracted files on a CPU-only environment.
4. Add the lightweight runtime dependencies through `requirements-ml-runtime.txt` in staging.
5. Run all backend tests with the artifact installed.
6. Compare model suggestions with deterministic plans in shadow mode before allowing fallback execution.

Training checkpoints, raw data, FP32 exports, and Kaggle working files do not belong here.
