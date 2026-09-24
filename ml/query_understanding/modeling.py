"""Tiny shared encoder with intent and token-classification heads."""

from __future__ import annotations

import json
from pathlib import Path

import torch
from torch import nn
from transformers import AutoConfig, AutoModel


class ClassWireTinyNluModel(nn.Module):
    """One compact encoder serving intent detection and entity extraction."""

    def __init__(
        self,
        base_model: str,
        intent_count: int,
        slot_count: int,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        config = AutoConfig.from_pretrained(base_model)
        self.encoder = AutoModel.from_pretrained(base_model, config=config)
        self.dropout = nn.Dropout(dropout)
        self.intent_projection = nn.Sequential(
            nn.Linear(config.hidden_size * 2, config.hidden_size),
            nn.GELU(),
            nn.LayerNorm(config.hidden_size),
            nn.Dropout(dropout),
        )
        self.intent_classifier = nn.Linear(config.hidden_size, intent_count)
        self.slot_classifier = nn.Linear(config.hidden_size, slot_count)
        self.base_model = base_model
        self.intent_count = intent_count
        self.slot_count = slot_count
        self.dropout_rate = dropout

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
        mean_pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        pooled = self.intent_projection(torch.cat((hidden[:, 0], mean_pooled), dim=-1))
        sequence = self.dropout(hidden)
        return self.intent_classifier(pooled), self.slot_classifier(sequence)


def save_checkpoint(
    model: ClassWireTinyNluModel,
    destination: str | Path,
    *,
    intent_labels: list[str],
    slot_labels: list[str],
    max_length: int,
    metadata: dict,
) -> None:
    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path / "model_state.pt")
    config = {
        "base_model": model.base_model,
        "dropout": model.dropout_rate,
        "intent_labels": intent_labels,
        "slot_labels": slot_labels,
        "max_length": max_length,
        **metadata,
    }
    (path / "model_config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_checkpoint(source: str | Path, device: torch.device):
    path = Path(source)
    config = json.loads((path / "model_config.json").read_text(encoding="utf-8"))
    model = ClassWireTinyNluModel(
        base_model=config["base_model"],
        intent_count=len(config["intent_labels"]),
        slot_count=len(config["slot_labels"]),
        dropout=float(config["dropout"]),
    )
    state = torch.load(path / "model_state.pt", map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    return model, config
