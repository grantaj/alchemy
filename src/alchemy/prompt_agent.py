import json
import re

from pydantic import BaseModel, Field

from alchemy.ollama_client import OllamaClient


class PromptPacket(BaseModel):
    positive_prompt: str
    negative_prompt: str = "text, watermark, detail, low quality"
    state_summary: str = ""
    denoise_strength: float = Field(default=0.45, ge=0.0, le=1.0)
    reset: bool = False


SYSTEM_PROMPT = """You convert spoken language fragments into concise image-generation prompts.
Preserve continuity with the previous visual state.
Prefer vivid concrete visual language over literal illustration.
Return JSON only.
Do not explain."""


def refine_prompt(
    client: OllamaClient,
    *,
    phrase: str,
    style: str,
    previous_prompt: str = "",
    state_summary: str = "",
    negative_prompt: str = "text, watermark, detail, low quality",
) -> PromptPacket:
    prompt = f"""Spoken phrase:
{phrase}

Pinned visual style:
{style}

Previous prompt:
{previous_prompt or "(none)"}

Previous visual state:
{state_summary or "(none)"}

Return this exact JSON shape:
{{
  "positive_prompt": "compact stable diffusion prompt",
  "negative_prompt": "{negative_prompt}",
  "state_summary": "short continuity summary",
  "denoise_strength": 0.45,
  "reset": false
}}"""

    response = client.generate_json(system=SYSTEM_PROMPT, prompt=prompt)
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
