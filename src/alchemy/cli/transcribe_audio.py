import argparse
import json
from pathlib import Path

from alchemy.audio_chunks import ChunkingConfig, chunk_segments
from alchemy.config import load_settings
from alchemy.speech_to_text import WhisperCppClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe an audio file with whisper.cpp.")
    parser.add_argument("audio_path", type=Path, help="Audio file to transcribe.")
    parser.add_argument("--language", default="en", help="Transcription language.")
    parser.add_argument("--segments", action="store_true", help="Print whisper.cpp segments as JSON.")
    parser.add_argument("--chunks", action="store_true", help="Print configured transcript chunks as JSON.")
    parser.add_argument("--max-seconds", type=float, help="Chunk max duration override.")
    parser.add_argument("--max-words", type=int, help="Chunk max word count override.")
    parser.add_argument("--min-silence-gap", type=float, help="Chunk silence gap override.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    if not args.audio_path.exists():
        raise SystemExit(f"Audio file does not exist: {args.audio_path}")

    client = WhisperCppClient(settings.whisper_cpp_inference_url)
    transcript = client.transcribe(args.audio_path, language=args.language)

    if args.segments:
        print(json.dumps([segment.model_dump() for segment in transcript.segments], indent=2))
        return

    if args.chunks:
        config = _chunking_config(settings, args)
        chunks = chunk_segments(transcript.segments, config)
        print(json.dumps([chunk.model_dump() for chunk in chunks], indent=2))
        return

    print(transcript.text)


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
