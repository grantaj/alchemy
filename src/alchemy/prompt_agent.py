import json
import re

from typing import Any

from pydantic import BaseModel, Field, field_validator

from alchemy.ollama_client import OllamaClient
from alchemy.prompt_profile import PromptProfile


class PromptPacket(BaseModel):
    poetic_response: str = ""
    content_anchor: str = ""
    positive_prompt: str
    negative_prompt: str = "text, watermark, detail, low quality"
    state_summary: str = ""
    denoise_strength: float = Field(default=0.68, ge=0.0, le=1.0)
    reset: bool = False

    @field_validator(
        "poetic_response",
        "content_anchor",
        "positive_prompt",
        "negative_prompt",
        "state_summary",
        mode="before",
    )
    @classmethod
    def _coerce_text_field(cls, value: Any) -> str:
        return _coerce_text(value)


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
    pinned_style = (style or profile.style).strip()
    prompt = profile.render(
        transcription=transcription,
        style=pinned_style,
        previous_prompt=previous_prompt,
        state_summary=state_summary,
        negative_prompt=negative_prompt,
    )
    response = client.generate_json(system=profile.system, prompt=prompt)
    packet = PromptPacket.model_validate(_loads_json_object(response))
    content_anchor = _poetic_response_anchor(packet.poetic_response)
    positive_prompt = _ensure_style_prefix(packet.positive_prompt, pinned_style)
    positive_prompt = _ensure_content_anchor(
        positive_prompt,
        content_anchor=content_anchor,
        pinned_style=pinned_style,
    )
    return packet.model_copy(
        update={
            "content_anchor": content_anchor,
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
        }
    )


def _ensure_style_prefix(positive_prompt: str, pinned_style: str) -> str:
    if not pinned_style:
        return positive_prompt

    normalized_prompt = positive_prompt.casefold()
    normalized_style = pinned_style.casefold()
    style_anchor = normalized_style.split(",", maxsplit=1)[0].strip()
    if normalized_style in normalized_prompt or (
        style_anchor and normalized_prompt.startswith(style_anchor)
    ):
        return positive_prompt

    return f"{pinned_style}, {positive_prompt}"


def _ensure_content_anchor(
    positive_prompt: str,
    *,
    content_anchor: str,
    pinned_style: str,
) -> str:
    if not content_anchor:
        return positive_prompt

    anchor_phrase = f"visible material evidence of {content_anchor}"
    if content_anchor.casefold() in positive_prompt.casefold():
        return positive_prompt

    if pinned_style and positive_prompt.startswith(pinned_style):
        return positive_prompt.replace(pinned_style, f"{pinned_style}, {anchor_phrase}", 1)

    return f"{anchor_phrase}, {positive_prompt}"


def _poetic_response_anchor(poetic_response: str) -> str:
    return " ".join(poetic_response.split())


def _loads_json_object(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Ollama did not return a JSON object: {text}")

    return json.loads(match.group(0))


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text

        parts = [_coerce_text(item) for item in value.values()]
        return ", ".join(part for part in parts if part)

    if isinstance(value, list):
        parts = [_coerce_text(item) for item in value]
        return ", ".join(part for part in parts if part)

    return str(value)
