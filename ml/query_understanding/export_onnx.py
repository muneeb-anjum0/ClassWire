"""Export, quantize, and package a trained checkpoint for the Flask runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoTokenizer

from ml.query_understanding.modeling import load_checkpoint


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/query_understanding/output/v1"))
    parser.add_argument("--model-version", default="tinybert-nlu-v1")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    device = torch.device("cpu")
    model, config = load_checkpoint(args.checkpoint, device)
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint / "tokenizer", use_fast=True)
    sample = tokenizer(
        "Show BSSE7A classes on Monday",
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=int(config["max_length"]),
    )

    fp32_path = args.output / "classwire_nlu.fp32.onnx"
    int8_path = args.output / "classwire_nlu.int8.onnx"
    torch.onnx.export(
        model,
        (sample["input_ids"], sample["attention_mask"]),
        fp32_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["intent_logits", "slot_logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "intent_logits": {0: "batch"},
            "slot_logits": {0: "batch", 1: "sequence"},
        },
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    quantize_dynamic(
        model_input=str(fp32_path),
        model_output=str(int8_path),
        weight_type=QuantType.QInt8,
    )
    onnx.checker.check_model(str(int8_path))
    validation_session = ort.InferenceSession(
        str(int8_path), providers=["CPUExecutionProvider"]
    )
    validation_outputs = validation_session.run(
        ["intent_logits", "slot_logits"],
        {
            "input_ids": sample["input_ids"].numpy().astype(np.int64),
            "attention_mask": sample["attention_mask"].numpy().astype(np.int64),
        },
    )
    expected_shapes = (
        (1, len(config["intent_labels"])),
        (1, int(config["max_length"]), len(config["slot_labels"])),
    )
    actual_shapes = tuple(tuple(output.shape) for output in validation_outputs)
    if actual_shapes != expected_shapes or not all(np.isfinite(output).all() for output in validation_outputs):
        raise RuntimeError(
            f"Export validation failed: expected {expected_shapes}, received {actual_shapes}"
        )

    tokenizer.backend_tokenizer.save(str(args.output / "tokenizer.json"))
    (args.output / "intent_labels.json").write_text(
        json.dumps(config["intent_labels"], indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "slot_labels.json").write_text(
        json.dumps(config["slot_labels"], indent=2) + "\n", encoding="utf-8"
    )
    metadata = {
        "model_version": args.model_version,
        "base_model": config["base_model"],
        "max_length": int(config["max_length"]),
        "intent_count": len(config["intent_labels"]),
        "slot_count": len(config["slot_labels"]),
        "quantization": "dynamic-int8",
        "onnx_opset": 17,
        "model_sha256": sha256(int8_path),
        "best_validation": config.get("best_validation", {}),
        "export_validation": {
            "finite_outputs": True,
            "intent_shape": list(actual_shapes[0]),
            "slot_shape": list(actual_shapes[1]),
        },
    }
    (args.output / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fp32_bytes = fp32_path.stat().st_size
    int8_bytes = int8_path.stat().st_size
    fp32_path.unlink()
    print(json.dumps({
        "artifact": str(args.output),
        "fp32_bytes": fp32_bytes,
        "int8_bytes": int8_bytes,
        "size_reduction_percent": round((1 - int8_bytes / fp32_bytes) * 100, 2),
        **metadata,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
