import argparse
from dataclasses import dataclass
from pathlib import Path
import queue
import tempfile
import threading
import time
import wave

from alchemy.audio_chunks import TranscriptChunk
from alchemy.cli.from_audio import _RuntimeState, _chunking_config, _process_chunk
from alchemy.config import load_settings
from alchemy.generation import ensure_initial_image
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_profile import load_prompt_profile
from alchemy.speech_to_text import WhisperCppClient


@dataclass(frozen=True)
class _RecordedAudio:
    index: int
    start: float
    end: float
    samples: object


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description="Capture microphone audio, transcribe phrases, and submit images to ComfyUI."
    )
    parser.add_argument("--language", default="en", help="Transcription language.")
    parser.add_argument(
        "--phrase-seconds",
        type=float,
        default=settings.alchemy_chunk_max_seconds,
        help="Microphone phrase window duration. Defaults to ALCHEMY_CHUNK_MAX_SECONDS.",
    )
    parser.add_argument("--sample-rate", type=int, default=16000, help="Microphone sample rate.")
    parser.add_argument("--device", help="sounddevice input device name or index.")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit.")
    parser.add_argument("--feedback", action="store_true", help="Use img2img feedback.")
    parser.add_argument("--denoise", type=float, help="Override img2img denoise strength.")
    parser.add_argument(
        "--backpressure",
        choices=("serial", "latest"),
        default=settings.alchemy_backpressure_mode,
        help="Policy when generation falls behind microphone capture.",
    )
    parser.add_argument("--monitor", action="store_true", help="Print detailed diagnostics.")
    parser.add_argument("--negative", help="Negative prompt override.")
    parser.add_argument("--profile", type=Path, help="Prompt profile TOML path.")
    parser.add_argument("--style", help="Pinned visual style override.")
    parser.add_argument("--previous-prompt", default="", help="Previous prompt context.")
    parser.add_argument("--state-summary", default="", help="Previous visual state context.")
    parser.add_argument("--seed", type=int, help="Seed override. Defaults to a random seed.")
    parser.add_argument("--workflow", type=Path, help="Txt2img workflow JSON path.")
    parser.add_argument("--prefix", default="alchemy_mic", help="ComfyUI output filename prefix.")
    parser.add_argument("--max-words", type=int, help="Expected chunk max word count for diagnostics.")
    parser.add_argument("--max-seconds", type=float, help="Expected chunk max duration for diagnostics.")
    parser.add_argument("--min-silence-gap", type=float, help="Expected chunk silence gap for diagnostics.")
    parser.set_defaults(chunked=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    if args.list_devices:
        print(_sounddevice().query_devices())
        return

    _validate_args(args)

    negative_prompt = args.negative or settings.alchemy_default_negative
    ollama = OllamaClient(settings.ollama_host, settings.ollama_model)
    profile = load_prompt_profile(args.profile or settings.alchemy_prompt_profile)
    whisper = WhisperCppClient(settings.whisper_cpp_inference_url)
    runtime = _RuntimeState(
        previous_prompt=args.previous_prompt,
        state_summary=args.state_summary,
        previous_image=ensure_initial_image(settings) if args.feedback else None,
        is_initial_image=bool(args.feedback),
    )

    _chunking_config(settings, args)
    recorder = _MicrophoneRecorder(
        sample_rate=args.sample_rate,
        phrase_seconds=args.phrase_seconds,
        device=args.device,
    )

    print("Microphone mode")
    print(f"  phrase_seconds: {args.phrase_seconds}")
    print(f"  sample_rate: {args.sample_rate}")
    print(f"  feedback: {args.feedback}")
    print("  stop: Ctrl+C")
    print()

    start_time = time.monotonic()
    processed = 0
    with recorder:
        try:
            while True:
                recorded = recorder.next_chunk()
                skipped = 0
                if args.backpressure == "latest":
                    recorded, skipped = recorder.latest_chunk(recorded)

                if skipped:
                    print(f"Backpressure: skipped {skipped} stale microphone phrase(s).")

                transcription = _transcribe_recording(whisper, recorded, args.language, args.sample_rate)
                if not transcription:
                    if args.monitor:
                        print(
                            f"[mic {recorded.index} {recorded.start:05.2f}s -> "
                            f"{recorded.end:05.2f}s] empty transcription"
                        )
                    continue

                processed += 1
                chunk = TranscriptChunk(
                    text=transcription,
                    start=recorded.start,
                    end=recorded.end,
                    word_count=len(transcription.split()),
                )
                _process_chunk(
                    processed,
                    processed,
                    chunk,
                    runtime,
                    settings,
                    args,
                    ollama,
                    profile,
                    negative_prompt,
                    scheduled_start=start_time,
                    delay_scale=1.0,
                )
        except KeyboardInterrupt:
            print("\nStopping microphone capture.")


def _validate_args(args: argparse.Namespace) -> None:
    if args.phrase_seconds <= 0:
        raise SystemExit("--phrase-seconds must be greater than 0.")

    if args.sample_rate <= 0:
        raise SystemExit("--sample-rate must be greater than 0.")


class _MicrophoneRecorder:
    def __init__(self, *, sample_rate: int, phrase_seconds: float, device: str | None) -> None:
        self.sample_rate = sample_rate
        self.phrase_seconds = phrase_seconds
        self.device = _device_value(device)
        self._raw_audio: queue.Queue[object] = queue.Queue()
        self._phrases: queue.Queue[_RecordedAudio] = queue.Queue()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream = None

    def __enter__(self) -> "_MicrophoneRecorder":
        sd = _sounddevice()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=self._audio_callback,
        )
        self._thread = threading.Thread(target=self._collect_phrases, daemon=True)
        self._thread.start()
        self._stream.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._stop.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        self._raw_audio.put(None)
        if self._thread is not None:
            self._thread.join(timeout=2)

    def next_chunk(self) -> _RecordedAudio:
        return self._phrases.get()

    def latest_chunk(self, current: _RecordedAudio) -> tuple[_RecordedAudio, int]:
        latest = current
        skipped = 0
        while True:
            try:
                latest = self._phrases.get_nowait()
                skipped += 1
            except queue.Empty:
                return latest, skipped

    def _audio_callback(self, indata, frames, callback_time, status) -> None:
        if status:
            print(status)
        self._raw_audio.put(indata.copy())

    def _collect_phrases(self) -> None:
        np = _numpy()
        phrase_frames = int(self.sample_rate * self.phrase_seconds)
        buffers = []
        buffered_frames = 0
        index = 1

        while not self._stop.is_set():
            block = self._raw_audio.get()
            if block is None:
                return

            buffers.append(block)
            buffered_frames += len(block)

            while buffered_frames >= phrase_frames:
                audio = np.concatenate(buffers, axis=0)
                phrase = audio[:phrase_frames]
                remainder = audio[phrase_frames:]
                start = (index - 1) * self.phrase_seconds
                end = index * self.phrase_seconds
                self._phrases.put(_RecordedAudio(index=index, start=start, end=end, samples=phrase))
                index += 1
                buffers = [remainder] if len(remainder) else []
                buffered_frames = len(remainder)


def _transcribe_recording(
    whisper: WhisperCppClient,
    recorded: _RecordedAudio,
    language: str,
    sample_rate: int,
) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as audio_file:
        path = Path(audio_file.name)

    try:
        _write_wav(path, recorded.samples, sample_rate)
        return whisper.transcribe(path, language=language).text.strip()
    finally:
        path.unlink(missing_ok=True)


def _write_wav(path: Path, samples: object, sample_rate: int) -> None:
    np = _numpy()
    audio = np.asarray(samples, dtype=np.float32).reshape(-1)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def _device_value(device: str | None) -> int | str | None:
    if device is None:
        return None

    try:
        return int(device)
    except ValueError:
        return device


def _sounddevice():
    try:
        import sounddevice as sd
    except ImportError as error:
        raise SystemExit(
            "sounddevice is required for microphone mode. Install the audio extra with "
            "`uv sync --extra audio`."
        ) from error
    except OSError as error:
        raise SystemExit(
            "PortAudio is required for microphone mode, but the native library was not found.\n"
            "Install it with `sudo apt install libportaudio2` on Debian/Ubuntu, or "
            "`brew install portaudio` on macOS, then retry `uv run alchemy-from-mic --list-devices`."
        ) from error
    return sd


def _numpy():
    try:
        import numpy as np
    except ImportError as error:
        raise SystemExit(
            "numpy is required for microphone mode. Install the audio extra with "
            "`uv sync --extra audio`."
        ) from error
    return np


if __name__ == "__main__":
    main()
