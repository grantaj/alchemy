import argparse
import json
from pathlib import Path

from alchemy.config import load_settings
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_agent import refine_prompt
from alchemy.prompt_profile import load_prompt_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refine a spoken phrase with Ollama.")
    parser.add_argument("transcription", help="Spoken phrase or transcript fragment.")
    parser.add_argument("--json", action="store_true", help="Print the full prompt packet as JSON.")
    parser.add_argument("--profile", type=Path, help="Prompt profile TOML path.")
    parser.add_argument("--style", help="Pinned visual style override.")
    parser.add_argument("--previous-prompt", default="", help="Previous positive prompt.")
    parser.add_argument("--state-summary", default="", help="Previous visual state summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    client = OllamaClient(settings.ollama_host, settings.ollama_model)
    profile = load_prompt_profile(settings.alchemy_prompt_profile if args.profile is None else args.profile)
    packet = refine_prompt(
        client,
        transcription=args.transcription,
        profile=profile,
        style=args.style or settings.alchemy_style,
        previous_prompt=args.previous_prompt,
        state_summary=args.state_summary,
        negative_prompt=settings.alchemy_default_negative,
    )
    if args.json:
        print(json.dumps(packet.model_dump(), indent=2))
        return

    if packet.poetic_response:
        print("Poetic response:")
        print(packet.poetic_response)
        print()
    if packet.content_anchor:
        print("Content anchor:")
        print(packet.content_anchor)
        print()
    print("Image prompt:")
    print(packet.positive_prompt)
    print()
    print("State summary:")
    print(packet.state_summary)


if __name__ == "__main__":
    main()
