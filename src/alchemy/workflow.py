import copy
import json
import random
from pathlib import Path
from typing import Any


Workflow = dict[str, Any]


def load_workflow(path: Path) -> Workflow:
    with path.open("r", encoding="utf-8") as workflow_file:
        return json.load(workflow_file)


def prepare_txt2img_workflow(
    workflow: Workflow,
    *,
    positive_prompt: str,
    negative_prompt: str | None = None,
    seed: int | None = None,
    filename_prefix: str | None = None,
) -> Workflow:
    """Mutate a ComfyUI API workflow exported from the current txt2img graph."""

    prepared = copy.deepcopy(workflow)

    prepared["6"]["inputs"]["text"] = positive_prompt

    if negative_prompt is not None:
        prepared["7"]["inputs"]["text"] = negative_prompt

    prepared["3"]["inputs"]["seed"] = seed if seed is not None else random.randrange(1, 2**63)

    if filename_prefix is not None:
        prepared["9"]["inputs"]["filename_prefix"] = filename_prefix

    return prepared


def prepare_img2img_workflow(
    workflow: Workflow,
    *,
    positive_prompt: str,
    input_image: str,
    negative_prompt: str | None = None,
    seed: int | None = None,
    denoise_strength: float | None = None,
    filename_prefix: str | None = None,
) -> Workflow:
    """Mutate a ComfyUI API workflow exported from the current img2img graph."""

    prepared = copy.deepcopy(workflow)

    prepared["6"]["inputs"]["text"] = positive_prompt
    prepared["10"]["inputs"]["image"] = input_image

    if negative_prompt is not None:
        prepared["7"]["inputs"]["text"] = negative_prompt

    prepared["3"]["inputs"]["seed"] = seed if seed is not None else random.randrange(1, 2**63)

    if denoise_strength is not None:
        prepared["3"]["inputs"]["denoise"] = denoise_strength

    if filename_prefix is not None:
        prepared["9"]["inputs"]["filename_prefix"] = filename_prefix

    return prepared
