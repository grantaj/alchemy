import argparse
import json

from alchemy.config import load_settings
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_agent import refine_prompt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refine a spoken phrase with Ollama.")
    parser.add_argument("phrase", help="Spoken phrase or transcript fragment.")
    parser.add_argument("--style", help="Pinned visual style override.")
    parser.add_argument("--previous-prompt", default="", help="Previous positive prompt.")
    parser.add_argument("--state-summary", default="", help="Previous visual state summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    client = OllamaClient(settings.ollama_host, settings.ollama_model)
    packet = refine_prompt(
        client,
        phrase=args.phrase,
        style=args.style or settings.alchemy_style,
        previous_prompt=args.previous_prompt,
        state_summary=args.state_summary,
        negative_prompt=settings.alchemy_default_negative,
    )
    print(json.dumps(packet.model_dump(), indent=2))


if __name__ == "__main__":
    main()
