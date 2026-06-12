"""Encoderfile HTTP client for encoder/classification models."""

from __future__ import annotations

import json
from typing import Any

import requests

from agent.config import get_settings


class EncoderfileClient:
    """Client for encoderfile REST API (/health, /model, /predict)."""

    def __init__(self, base_url: str | None = None, timeout: int = 30) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.encoderfile_base_url).rstrip("/")
        self.timeout = timeout
        self._model_info: dict[str, Any] | None = None

    def health(self) -> bool:
        response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
        response.raise_for_status()
        body = response.text.strip().strip('"')
        return body == "OK!"

    def model_info(self) -> dict[str, Any]:
        if self._model_info is None:
            response = requests.get(f"{self.base_url}/model", timeout=self.timeout)
            response.raise_for_status()
            self._model_info = response.json()
        return self._model_info

    def predict(self, inputs: list[str], **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"inputs": inputs, **kwargs}
        response = requests.post(
            f"{self.base_url}/predict",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def predict_text(self, text: str, **kwargs: Any) -> str:
        result = self.predict([text], **kwargs)
        return json.dumps(result, indent=2)

    def summarize_prediction(self, text: str, **kwargs: Any) -> str:
        result = self.predict([text], **kwargs)
        model_type = self.model_info().get("model_type")
        results = result.get("results", [])
        if not results:
            return "No prediction returned."

        first = results[0]
        if model_type == "sequence_classification":
            label = first.get("predicted_label", first.get("predicted_index"))
            scores = first.get("scores", [0])
            score = max(scores) if scores else 0
            return f"Classification for '{text}': {label} (confidence {score:.4f})"

        if model_type == "token_classification":
            entities = [
                f"{token['token_info']['token']}={token['label']}"
                for token in first.get("tokens", [])
                if token.get("label") not in {"O", "0"}
            ]
            return f"Token labels for '{text}': {', '.join(entities) or 'none detected'}"

        if model_type == "embedding":
            count = len(first.get("embeddings", []))
            return f"Generated {count} token embeddings for '{text}'."

        return json.dumps(first, indent=2)
