import argparse
from pathlib import Path

from alchemy.config import load_settings
from alchemy.speech_to_text import WhisperCppClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe an audio file with whisper.cpp.")
    parser.add_argument("audio_path", type=Path, help="Audio file to transcribe.")
    parser.add_argument("--language", default="en", help="Transcription language.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    if not args.audio_path.exists():
        raise SystemExit(f"Audio file does not exist: {args.audio_path}")

    client = WhisperCppClient(settings.whisper_cpp_inference_url)
    transcription = client.transcribe_file(args.audio_path, language=args.language)
    print(transcription)


if __name__ == "__main__":
    main()
