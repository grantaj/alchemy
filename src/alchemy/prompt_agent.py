import json
import re

from pydantic import BaseModel, Field

from alchemy.ollama_client import OllamaClient
from alchemy.prompt_profile import PromptProfile


class PromptPacket(BaseModel):
    poetic_response: str = ""
    positive_prompt: str
    negative_prompt: str = "text, watermark, detail, low quality"
    state_summary: str = ""
    denoise_strength: float = Field(default=0.45, ge=0.0, le=1.0)
    reset: bool = False


def refine_prompt(
    client: OllamaClient,
    *,
    transcription: str,
    profile: PromptProfile,
    style: str | None = None,
    previous_prompt: str = "",
    state_summary: str = "",
    negative_prompt: str = "text, watermark, detail, low quality",
) -> PromptPacket:
    prompt = profile.render(
        transcription=transcription,
        style=style,
        previous_prompt=previous_prompt,
        state_summary=state_summary,
        negative_prompt=negative_prompt,
    )
    response = client.generate_json(system=profile.system, prompt=prompt)
    packet = PromptPacket.model_validate(_loads_json_object(response))
    return packet.model_copy(update={"negative_prompt": negative_prompt})


def _loads_json_object(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Ollama did not return a JSON object: {text}")

    return json.loads(match.group(0))
