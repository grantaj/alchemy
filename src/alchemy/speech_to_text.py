from pathlib import Path
import subprocess
import tempfile
from typing import Any

from pydantic import BaseModel
import requests


class TranscriptWord(BaseModel):
    word: str
    start: float | None = None
    end: float | None = None


class TranscriptSegment(BaseModel):
    text: str
    start: float | None = None
    end: float | None = None
    words: list[TranscriptWord] = []


class Transcript(BaseModel):
    text: str
    segments: list[TranscriptSegment] = []


class WhisperCppClient:
    def __init__(self, inference_url: str) -> None:
        self.inference_url = inference_url

    def transcribe_file(self, path: Path, *, language: str = "en") -> str:
        return self.transcribe(path, language=language).text

    def transcribe(self, path: Path, *, language: str = "en") -> Transcript:
        if path.suffix.lower() == ".wav":
            return self._transcribe_wav(path, language=language)

        with tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
            wav_path = Path(wav_file.name)
            _convert_to_wav(path, wav_path)
            return self._transcribe_wav(wav_path, language=language)

    def _transcribe_wav(self, path: Path, *, language: str) -> Transcript:
        with path.open("rb") as audio_file:
            response = requests.post(
                self.inference_url,
                files={"file": (path.name, audio_file)},
                data={
                    "temperature": "0.0",
                    "temperature_inc": "0.2",
                    "response_format": "verbose_json",
                    "language": language,
                },
                timeout=300,
            )

        response.raise_for_status()
        return _extract_transcript(response)


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


def _extract_transcript(response: requests.Response) -> Transcript:
    content_type = response.headers.get("content-type", "")

    if "application/json" not in content_type:
        return Transcript(text=response.text.strip())

    payload: dict[str, Any] = response.json()
    text = _payload_text(payload)
    segments = _payload_segments(payload)
    return Transcript(text=text, segments=segments)


def _payload_text(payload: dict[str, Any]) -> str:
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


def _payload_segments(payload: dict[str, Any]) -> list[TranscriptSegment]:
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        return []

    segments: list[TranscriptSegment] = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            continue
        segments.append(
            TranscriptSegment(
                text=str(raw_segment.get("text", "")).strip(),
                start=_optional_float(raw_segment.get("start")),
                end=_optional_float(raw_segment.get("end")),
                words=_payload_words(raw_segment),
            )
        )
    return segments


def _payload_words(segment: dict[str, Any]) -> list[TranscriptWord]:
    raw_words = segment.get("words")
    if not isinstance(raw_words, list):
        return []

    words: list[TranscriptWord] = []
    for raw_word in raw_words:
        if not isinstance(raw_word, dict):
            continue
        words.append(
            TranscriptWord(
                word=str(raw_word.get("word", "")),
                start=_optional_float(raw_word.get("start")),
                end=_optional_float(raw_word.get("end")),
            )
        )
    return words


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
