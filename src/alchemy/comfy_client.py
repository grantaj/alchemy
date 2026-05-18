import json
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
import websocket


@dataclass(frozen=True)
class ComfyOutput:
    filename: str
    subfolder: str
    type: str


class ComfyClient:
    def __init__(self, base_url: str, ws_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.ws_url = ws_url
        self.client_id = str(uuid.uuid4())

    def submit(self, workflow: dict[str, Any]) -> str:
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": self.client_id},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["prompt_id"]

    def wait_for_prompt(self, prompt_id: str) -> None:
        ws = websocket.WebSocket()
        ws.connect(f"{self.ws_url}?{urlencode({'clientId': self.client_id})}")
        try:
            while True:
                message = ws.recv()
                if not isinstance(message, str):
                    continue

                event = json.loads(message)
                if event.get("type") != "executing":
                    continue

                data = event.get("data", {})
                if data.get("prompt_id") == prompt_id and data.get("node") is None:
                    return
        finally:
            ws.close()

    def history(self, prompt_id: str) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        return response.json()[prompt_id]

    def first_image_output(self, prompt_id: str) -> ComfyOutput:
        history = self.history(prompt_id)

        for node_output in history.get("outputs", {}).values():
            for image in node_output.get("images", []):
                return ComfyOutput(
                    filename=image["filename"],
                    subfolder=image.get("subfolder", ""),
                    type=image.get("type", "output"),
                )

        raise RuntimeError(f"No image output found for prompt {prompt_id}")
