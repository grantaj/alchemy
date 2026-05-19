from dataclasses import dataclass
from pathlib import Path
from shutil import copy2

from alchemy.comfy_client import ComfyClient
from alchemy.config import Settings
from alchemy.image_state import copy_current_image
from alchemy.workflow import (
    Workflow,
    load_workflow,
    prepare_img2img_workflow,
    prepare_txt2img_workflow,
)


@dataclass(frozen=True)
class GenerationResult:
    prompt_id: str
    current_image: Path | None
    comfy_filename: str


def submit_txt2img(
    settings: Settings,
    *,
    positive_prompt: str,
    negative_prompt: str,
    workflow_path: Path | None = None,
    seed: int | None = None,
    filename_prefix: str = "alchemy",
) -> GenerationResult:
    workflow = load_workflow(workflow_path or settings.alchemy_workflow)
    prepared = prepare_txt2img_workflow(
        workflow,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        filename_prefix=filename_prefix,
    )
    return submit_prepared_workflow(settings, prepared)


def submit_img2img(
    settings: Settings,
    *,
    positive_prompt: str,
    negative_prompt: str,
    source_image: Path,
    workflow_path: Path | None = None,
    seed: int | None = None,
    denoise_strength: float | None = None,
    filename_prefix: str = "alchemy",
) -> GenerationResult:
    input_image_name = stage_comfy_input_image(settings, source_image)
    workflow = load_workflow(workflow_path or settings.alchemy_feedback_workflow)
    prepared = prepare_img2img_workflow(
        workflow,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        input_image=input_image_name,
        seed=seed,
        denoise_strength=denoise_strength,
        filename_prefix=filename_prefix,
    )
    return submit_prepared_workflow(settings, prepared)


def stage_comfy_input_image(settings: Settings, source_image: Path) -> str:
    if settings.comfy_input_dir is None:
        raise RuntimeError("COMFY_INPUT_DIR must be set to use img2img feedback.")

    if not source_image.exists():
        raise RuntimeError(f"Feedback source image does not exist: {source_image}")

    settings.comfy_input_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.comfy_input_dir / "alchemy_feedback.png"
    copy2(source_image, destination)
    return destination.name


def submit_prepared_workflow(settings: Settings, workflow: Workflow) -> GenerationResult:
    client = ComfyClient(settings.comfy_base_url, settings.comfy_ws_url)
    prompt_id = client.submit(workflow)
    print(f"Submitted prompt {prompt_id}")

    client.wait_for_prompt(prompt_id)
    output = client.first_image_output(prompt_id)

    current_image = None
    if settings.comfy_output_dir is not None:
        source = settings.comfy_output_dir / output.subfolder / output.filename
        current_image = copy_current_image(source, settings.alchemy_current_image)
        print(f"Updated {current_image}")
    else:
        print("Generated image:")
        print(f"  filename={output.filename}")
        print(f"  subfolder={output.subfolder}")
        print(f"  type={output.type}")
        print("Set COMFY_OUTPUT_DIR to copy this image to output/current.png.")

    return GenerationResult(
        prompt_id=prompt_id,
        current_image=current_image,
        comfy_filename=output.filename,
    )
