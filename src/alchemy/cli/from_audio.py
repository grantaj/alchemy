import argparse
from pathlib import Path

from alchemy.config import load_settings
from alchemy.generation import submit_txt2img
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_agent import refine_prompt
from alchemy.prompt_profile import load_prompt_profile
from alchemy.speech_to_text import WhisperCppClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file, refine it with Ollama, and submit to ComfyUI."
    )
    parser.add_argument("audio_path", type=Path, help="Audio file to process.")
    parser.add_argument("--language", default="en", help="Transcription language.")
    parser.add_argument("--negative", help="Negative prompt override.")
    parser.add_argument("--profile", type=Path, help="Prompt profile TOML path.")
    parser.add_argument("--style", help="Pinned visual style override.")
    parser.add_argument("--previous-prompt", default="", help="Previous prompt context.")
    parser.add_argument("--state-summary", default="", help="Previous visual state context.")
    parser.add_argument("--seed", type=int, help="Seed override. Defaults to a random seed.")
    parser.add_argument("--workflow", type=Path, help="Workflow JSON path.")
    parser.add_argument("--prefix", default="alchemy", help="ComfyUI output filename prefix.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    if not args.audio_path.exists():
        raise SystemExit(f"Audio file does not exist: {args.audio_path}")

    whisper = WhisperCppClient(settings.whisper_cpp_inference_url)
    transcription = whisper.transcribe_file(args.audio_path, language=args.language)
    print("Transcription:")
    print(f"  {transcription}")

    negative_prompt = args.negative or settings.alchemy_default_negative
    ollama = OllamaClient(settings.ollama_host, settings.ollama_model)
    profile = load_prompt_profile(args.profile or settings.alchemy_prompt_profile)
    packet = refine_prompt(
        ollama,
        transcription=transcription,
        profile=profile,
        style=args.style or settings.alchemy_style,
        previous_prompt=args.previous_prompt,
        state_summary=args.state_summary,
        negative_prompt=negative_prompt,
    )

    print("Poetic response:")
    print(f"  {packet.poetic_response}")
    print("Refined prompt:")
    print(f"  {packet.positive_prompt}")

    submit_txt2img(
        settings,
        positive_prompt=packet.positive_prompt,
        negative_prompt=packet.negative_prompt,
        workflow_path=args.workflow,
        seed=args.seed,
        filename_prefix=args.prefix,
    )


if __name__ == "__main__":
    main()
