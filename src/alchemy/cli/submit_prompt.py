import argparse
from pathlib import Path

from alchemy.config import load_settings
from alchemy.generation import submit_txt2img
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_agent import refine_prompt
from alchemy.prompt_profile import load_prompt_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit one prompt to the local ComfyUI workflow.")
    parser.add_argument("prompt", help="Positive prompt, or spoken phrase when --refine is set.")
    parser.add_argument("--negative", help="Negative prompt override.")
    parser.add_argument("--seed", type=int, help="Seed override. Defaults to a random seed.")
    parser.add_argument("--workflow", type=Path, help="Workflow JSON path.")
    parser.add_argument("--prefix", default="alchemy", help="ComfyUI output filename prefix.")
    parser.add_argument("--refine", action="store_true", help="Refine the prompt with Ollama first.")
    parser.add_argument("--profile", type=Path, help="Prompt profile TOML path for --refine.")
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
        profile = load_prompt_profile(args.profile or settings.alchemy_prompt_profile)
        packet = refine_prompt(
            ollama,
            transcription=args.prompt,
            profile=profile,
            style=args.style or settings.alchemy_style,
            previous_prompt=args.previous_prompt,
            state_summary=args.state_summary,
            negative_prompt=negative_prompt,
        )
        positive_prompt = packet.positive_prompt
        negative_prompt = packet.negative_prompt
        print("Poetic response:")
        print(f"  {packet.poetic_response}")
        print("Refined prompt:")
        print(f"  {positive_prompt}")

    submit_txt2img(
        settings,
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        workflow_path=workflow_path,
        seed=args.seed,
        filename_prefix=args.prefix,
    )


if __name__ == "__main__":
    main()
