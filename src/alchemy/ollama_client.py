from typing import Any

import requests


class OllamaClient:
    def __init__(self, host: str, model: str) -> None:
        self.host = host.rstrip("/")
        self.model = model

    def list_models(self) -> list[str]:
        response = requests.get(f"{self.host}/api/tags", timeout=5)
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]

    def has_model(self) -> bool:
        return self.model in self.list_models()

    def generate_json(self, *, system: str, prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.35,
                "num_predict": 320,
            },
        }
        response = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
