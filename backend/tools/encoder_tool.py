"""Tools backed by encoderfile for classification, NER, and embeddings."""

from __future__ import annotations

from functools import lru_cache

from encoder.encoder_client import EncoderfileClient


@lru_cache(maxsize=1)
def _client() -> EncoderfileClient:
    return EncoderfileClient()


def analyze_text(text: str) -> str:
    """Classify sentiment (POSITIVE/NEGATIVE) of text using encoderfile. Not for idiom meanings."""
    return _client().summarize_prediction(text)


def classify_sentiment(text: str) -> str:
    """Classify whether text is POSITIVE or NEGATIVE using the local encoderfile model."""
    return _client().summarize_prediction(text)


def get_text_embeddings(text: str, normalize: bool = True) -> str:
    """Generate token embeddings for text using the local encoderfile model."""
    return _client().predict_text(text, normalize=normalize)
