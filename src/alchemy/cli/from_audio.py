import argparse
from pathlib import Path

from alchemy.audio_chunks import ChunkingConfig, TranscriptChunk, chunk_segments
from alchemy.config import load_settings
from alchemy.generation import submit_img2img, submit_txt2img
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
    parser.add_argument("--chunked", action="store_true", help="Generate one image per transcript chunk.")
    parser.add_argument(
        "--feedback",
        action="store_true",
        help="Use img2img feedback after the first generated image.",
    )
    parser.add_argument("--denoise", type=float, help="Override img2img denoise strength.")
    parser.add_argument("--max-seconds", type=float, help="Chunk max duration override.")
    parser.add_argument("--max-words", type=int, help="Chunk max word count override.")
    parser.add_argument("--min-silence-gap", type=float, help="Chunk silence gap override.")
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
    transcript = whisper.transcribe(args.audio_path, language=args.language)
    transcription = transcript.text
    print("Transcription:")
    print(f"  {transcription}")

    negative_prompt = args.negative or settings.alchemy_default_negative
    ollama = OllamaClient(settings.ollama_host, settings.ollama_model)
    profile = load_prompt_profile(args.profile or settings.alchemy_prompt_profile)
    chunks = [_single_chunk(transcription)]
    if args.chunked:
        chunks = chunk_segments(transcript.segments, _chunking_config(settings, args))
        print(f"Chunks: {len(chunks)}")

    previous_prompt = args.previous_prompt
    state_summary = args.state_summary
    previous_image: Path | None = None
    for index, chunk in enumerate(chunks, start=1):
        if args.chunked:
            print(f"Chunk {index}/{len(chunks)}:")
            print(f"  {chunk.text}")

        packet = refine_prompt(
            ollama,
            transcription=chunk.text,
            profile=profile,
            style=args.style or settings.alchemy_style,
            previous_prompt=previous_prompt,
            state_summary=state_summary,
            negative_prompt=negative_prompt,
        )

        print("Poetic response:")
        print(f"  {packet.poetic_response}")
        print("Refined prompt:")
        print(f"  {packet.positive_prompt}")

        prefix = args.prefix if not args.chunked else f"{args.prefix}_chunk_{index:03d}"
        use_feedback = args.feedback and previous_image is not None
        if use_feedback:
            if args.denoise is None:
                print("Generation mode: img2img feedback, denoise=workflow default")
            else:
                print(f"Generation mode: img2img feedback, denoise={args.denoise}")
            result = submit_img2img(
                settings,
                positive_prompt=packet.positive_prompt,
                negative_prompt=packet.negative_prompt,
                source_image=previous_image,
                seed=args.seed,
                denoise_strength=args.denoise,
                filename_prefix=prefix,
            )
        else:
            print("Generation mode: txt2img")
            result = submit_txt2img(
                settings,
                positive_prompt=packet.positive_prompt,
                negative_prompt=packet.negative_prompt,
                workflow_path=args.workflow,
                seed=args.seed,
                filename_prefix=prefix,
            )

        previous_prompt = packet.positive_prompt
        state_summary = packet.state_summary
        previous_image = result.current_image


def _single_chunk(text: str) -> TranscriptChunk:
    return TranscriptChunk(text=text, word_count=len(text.split()))


def _chunking_config(settings, args: argparse.Namespace) -> ChunkingConfig:
    return ChunkingConfig(
        max_seconds=args.max_seconds or settings.alchemy_chunk_max_seconds,
        max_words=args.max_words or settings.alchemy_chunk_max_words,
        min_words=settings.alchemy_chunk_min_words,
        min_silence_gap=(
            args.min_silence_gap
            if args.min_silence_gap is not None
            else settings.alchemy_chunk_min_silence_gap
        ),
        prefer_sentence_boundary=settings.alchemy_chunk_prefer_sentence_boundary,
        sentence_punctuation=settings.alchemy_chunk_sentence_punctuation,
    )


if __name__ == "__main__":
    main()
