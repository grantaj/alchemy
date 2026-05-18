from pathlib import Path
import subprocess
import tempfile
from typing import Any

import requests


class WhisperCppClient:
    def __init__(self, inference_url: str) -> None:
        self.inference_url = inference_url

    def transcribe_file(self, path: Path, *, language: str = "en") -> str:
        if path.suffix.lower() == ".wav":
            return self._transcribe_wav(path, language=language)

        with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
            wav_path = Path(wav_file.name)
            _convert_to_wav(path, wav_path)
            return self._transcribe_wav(wav_path, language=language)

    def _transcribe_wav(self, path: Path, *, language: str) -> str:
        with path.open("rb") as audio_file:
            response = requests.post(
                self.inference_url,
                files={"file": (path.name, audio_file)},
                data={
                    "temperature": "0.0",
                    "temperature_inc": "0.2",
                    "response_format": "json",
                    "language": language,
                },
                timeout=300,
            )

        response.raise_for_status()
        return _extract_text(response)


def _convert_to_wav(source: Path, destination: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise RuntimeError("ffmpeg is required to transcribe non-WAV audio files") from error
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"ffmpeg could not convert {source}: {error.stderr}") from error


def _extract_text(response: requests.Response) -> str:
    content_type = response.headers.get("content-type", "")

    if "application/json" not in content_type:
        return response.text.strip()

    payload: dict[str, Any] = response.json()

    for key in ("text", "transcription", "result"):
        value = payload.get(key)
        if isinstance(value, str):
            return value.strip()

    segments = payload.get("segments")
    if isinstance(segments, list):
        text = " ".join(
            segment.get("text", "").strip()
            for segment in segments
            if isinstance(segment, dict)
        )
        if text:
            return text.strip()

    raise RuntimeError(f"Could not find transcription text in whisper.cpp response: {payload}")
