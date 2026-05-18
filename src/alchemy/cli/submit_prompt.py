import argparse
from pathlib import Path

from alchemy.comfy_client import ComfyClient
from alchemy.config import load_settings
from alchemy.image_state import copy_current_image
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_agent import refine_prompt
from alchemy.workflow import load_workflow, prepare_txt2img_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit one prompt to the local ComfyUI workflow.")
    parser.add_argument("prompt", help="Positive prompt, or spoken phrase when --refine is set.")
    parser.add_argument("--negative", help="Negative prompt override.")
    parser.add_argument("--seed", type=int, help="Seed override. Defaults to a random seed.")
    parser.add_argument("--workflow", type=Path, help="Workflow JSON path.")
    parser.add_argument("--prefix", default="alchemy", help="ComfyUI output filename prefix.")
    parser.add_argument("--refine", action="store_true", help="Refine the prompt with Ollama first.")
    parser.add_argument("--style", help="Pinned visual style override for --refine.")
    parser.add_argument("--previous-prompt", default="", help="Previous prompt context for --refine.")
    parser.add_argument("--state-summary", default="", help="Previous visual state context for --refine.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    workflow_path = args.workflow or settings.alchemy_workflow
    positive_prompt = args.prompt
    negative_prompt = args.negative or settings.alchemy_default_negative

    if args.refine:
        ollama = OllamaClient(settings.ollama_host, settings.ollama_model)
        packet = refine_prompt(
            ollama,
            phrase=args.prompt,
            style=args.style or settings.alchemy_style,
            previous_prompt=args.previous_prompt,
            state_summary=args.state_summary,
            negative_prompt=negative_prompt,
        )
        positive_prompt = packet.positive_prompt
        negative_prompt = packet.negative_prompt
        print("Refined prompt:")
        print(f"  {positive_prompt}")

    workflow = load_workflow(workflow_path)
    prepared = prepare_txt2img_workflow(
        workflow,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        seed=args.seed,
        filename_prefix=args.prefix,
    )

    client = ComfyClient(settings.comfy_base_url, settings.comfy_ws_url)
    prompt_id = client.submit(prepared)
    print(f"Submitted prompt {prompt_id}")

    client.wait_for_prompt(prompt_id)
    output = client.first_image_output(prompt_id)

    if settings.comfy_output_dir is None:
        print("Generated image:")
        print(f"  filename={output.filename}")
        print(f"  subfolder={output.subfolder}")
        print(f"  type={output.type}")
        print("Set COMFY_OUTPUT_DIR to copy this image to output/current.png.")
        return

    source = settings.comfy_output_dir / output.subfolder / output.filename
    current = copy_current_image(source, settings.alchemy_current_image)
    print(f"Updated {current}")


if __name__ == "__main__":
    main()
