"""Optional lightweight natural-language model support for ClassWire search."""

from .runtime import TinyNluRuntime, get_runtime, predict_with_optional_model
from .schema import EntityPrediction, NluPrediction

__all__ = [
    "EntityPrediction",
    "NluPrediction",
    "TinyNluRuntime",
    "get_runtime",
    "predict_with_optional_model",
]
