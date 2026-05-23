import argparse
from pathlib import Path
import shlex
import subprocess
import time

from alchemy.audio_chunks import ChunkingConfig, TranscriptChunk, chunk_segments
from alchemy.config import load_settings
from alchemy.generation import ensure_initial_image, submit_img2img, submit_txt2img
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
        help="Use img2img feedback for every chunk, starting from the initial image.",
    )
    parser.add_argument("--denoise", type=float, help="Override img2img denoise strength.")
    parser.add_argument("--max-seconds", type=float, help="Chunk max duration override.")
    parser.add_argument("--max-words", type=int, help="Chunk max word count override.")
    parser.add_argument("--min-silence-gap", type=float, help="Chunk silence gap override.")
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="Schedule chunk processing according to transcript timestamps.",
    )
    parser.add_argument("--delay-scale", type=float, help="Scale realtime delays, e.g. 0.5 is 2x.")
    parser.add_argument("--play-audio", action="store_true", help="Play the source audio during realtime mode.")
    parser.add_argument("--audio-player", help="Audio player command. Defaults to ALCHEMY_AUDIO_PLAYER.")
    parser.add_argument(
        "--backpressure",
        choices=("serial", "latest"),
        help="Realtime policy when generation falls behind.",
    )
    parser.add_argument("--monitor", action="store_true", help="Print detailed rehearsal diagnostics.")
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

    runtime = _RuntimeState(
        previous_prompt=args.previous_prompt,
        state_summary=args.state_summary,
        previous_image=ensure_initial_image(settings) if args.feedback else None,
        is_initial_image=bool(args.feedback),
    )
    if args.realtime:
        _process_realtime(chunks, runtime, settings, args, ollama, profile, negative_prompt)
    else:
        for index, chunk in enumerate(chunks, start=1):
            _process_chunk(
                index,
                len(chunks),
                chunk,
                runtime,
                settings,
                args,
                ollama,
                profile,
                negative_prompt,
                scheduled_start=None,
                delay_scale=1.0,
            )


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


class _RuntimeState:
    def __init__(
        self,
        *,
        previous_prompt: str,
        state_summary: str,
        previous_image: Path | None,
        is_initial_image: bool,
    ) -> None:
        self.previous_prompt = previous_prompt
        self.state_summary = state_summary
        self.previous_image = previous_image
        self.is_initial_image = is_initial_image


def _process_realtime(
    chunks: list[TranscriptChunk],
    runtime: _RuntimeState,
    settings,
    args: argparse.Namespace,
    ollama: OllamaClient,
    profile,
    negative_prompt: str,
) -> None:
    delay_scale = args.delay_scale if args.delay_scale is not None else settings.alchemy_delay_scale
    backpressure = args.backpressure or settings.alchemy_backpressure_mode
    if backpressure not in {"serial", "latest"}:
        raise SystemExit(f"Unsupported backpressure mode: {backpressure}")

    audio_process = _start_audio(args, settings) if args.play_audio else None
    start_time = time.monotonic()
    try:
        index = 0
        while index < len(chunks):
            chunk = chunks[index]
            _wait_for_chunk(chunk, start_time, delay_scale)
            _process_chunk(
                index + 1,
                len(chunks),
                chunk,
                runtime,
                settings,
                args,
                ollama,
                profile,
                negative_prompt,
                scheduled_start=start_time,
                delay_scale=delay_scale,
            )
            index += 1

            if backpressure == "latest":
                latest_ready = _latest_ready_chunk_index(chunks, start_time, delay_scale, index)
                if latest_ready is not None and latest_ready > index:
                    skipped = latest_ready - index
                    if args.monitor:
                        skipped_range = f"{index + 1}-{latest_ready}" if skipped > 1 else f"{index + 1}"
                        print("[backpressure]")
                        print(f"  skipped chunks: {skipped_range}")
                        print(f"  jumping to chunk: {latest_ready + 1}")
                    else:
                        print(
                            f"Backpressure: skipped {skipped} stale chunk(s); "
                            f"jumping to chunk {latest_ready + 1}."
                        )
                    index = latest_ready
    finally:
        if audio_process is not None:
            _finish_audio(audio_process)


def _start_audio(args: argparse.Namespace, settings) -> subprocess.Popen:
    command = shlex.split(args.audio_player or settings.alchemy_audio_player)
    if not command:
        raise RuntimeError("Audio player command is empty.")

    command.append(str(args.audio_path))
    if args.monitor:
        print("audio:")
        print(f"  player={' '.join(command)}")

    try:
        return subprocess.Popen(command)
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Audio player not found: {command[0]}. "
            "Set ALCHEMY_AUDIO_PLAYER or pass --audio-player."
        ) from error


def _finish_audio(audio_process: subprocess.Popen) -> None:
    if audio_process.poll() is not None:
        return

    try:
        audio_process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        # The visuals may finish before playback when chunks are skipped. Leave the
        # source audio playing rather than cutting off the room abruptly.
        pass


def _wait_for_chunk(chunk: TranscriptChunk, start_time: float, delay_scale: float) -> None:
    if chunk.start is None:
        return

    target = start_time + (chunk.start * delay_scale)
    remaining = target - time.monotonic()
    if remaining > 0:
        time.sleep(remaining)


def _latest_ready_chunk_index(
    chunks: list[TranscriptChunk],
    start_time: float,
    delay_scale: float,
    start_index: int,
) -> int | None:
    elapsed = (time.monotonic() - start_time) / delay_scale
    latest = None
    for index in range(start_index, len(chunks)):
        chunk_start = chunks[index].start
        if chunk_start is None or chunk_start <= elapsed:
            latest = index
        else:
            break
    return latest


def _process_chunk(
    index: int,
    total: int,
    chunk: TranscriptChunk,
    runtime: _RuntimeState,
    settings,
    args: argparse.Namespace,
    ollama: OllamaClient,
    profile,
    negative_prompt: str,
    scheduled_start: float | None,
    delay_scale: float,
) -> None:
    started_at = time.monotonic()
    lag = _chunk_lag(chunk, scheduled_start, delay_scale)

    if args.chunked:
        timing = _format_chunk_timing(chunk)
        if args.monitor:
            print()
            print(f"[chunk {index}/{total}{timing} | {chunk.word_count} words]")
            if lag is not None:
                print(f"lag: {lag:+.2f}s")
            print("transcript:")
            print(f"  {chunk.text}")
        else:
            print(f"Chunk {index}/{total}{timing}:")
            print(f"  {chunk.text}")

    refine_started = time.monotonic()
    packet = refine_prompt(
        ollama,
        transcription=chunk.text,
        profile=profile,
        style=args.style or settings.alchemy_style,
        previous_prompt=runtime.previous_prompt,
        state_summary=runtime.state_summary,
        negative_prompt=negative_prompt,
    )
    refine_duration = time.monotonic() - refine_started

    if args.monitor:
        if packet.poetic_response:
            print("poetic:")
            print(f"  {packet.poetic_response}")
        if packet.content_anchor:
            print("anchor:")
            print(f"  {packet.content_anchor}")
        print("prompt:")
        print(f"  {packet.positive_prompt}")
    else:
        if packet.poetic_response:
            print("Poetic response:")
            print(f"  {packet.poetic_response}")
        if packet.content_anchor:
            print("Content anchor:")
            print(f"  {packet.content_anchor}")
        print("Refined prompt:")
        print(f"  {packet.positive_prompt}")

    prefix = args.prefix if not args.chunked else f"{args.prefix}_chunk_{index:03d}"
    use_feedback = args.feedback and runtime.previous_image is not None
    generation_started = time.monotonic()
    if use_feedback:
        if runtime.is_initial_image:
            denoise_strength = settings.alchemy_initial_denoise
            denoise_label = f"initial {denoise_strength}"
        elif args.denoise is None:
            denoise_strength = packet.denoise_strength
            mode = "img2img feedback"
            denoise_label = f"prompt {packet.denoise_strength}"
        else:
            denoise_strength = args.denoise
            mode = "img2img feedback"
            denoise_label = str(args.denoise)
        mode = "img2img feedback"
        if not args.monitor:
            print(f"Generation mode: {mode}, denoise={denoise_label}")
        result = submit_img2img(
            settings,
            positive_prompt=packet.positive_prompt,
            negative_prompt=packet.negative_prompt,
            source_image=runtime.previous_image,
            seed=args.seed,
            denoise_strength=denoise_strength,
            filename_prefix=prefix,
            quiet=args.monitor,
        )
    else:
        mode = "txt2img"
        denoise_label = None
        if not args.monitor:
            print(f"Generation mode: {mode}")
        result = submit_txt2img(
            settings,
            positive_prompt=packet.positive_prompt,
            negative_prompt=packet.negative_prompt,
            workflow_path=args.workflow,
            seed=args.seed,
            filename_prefix=prefix,
            quiet=args.monitor,
        )
    generation_duration = time.monotonic() - generation_started

    runtime.previous_prompt = packet.positive_prompt
    runtime.state_summary = packet.state_summary
    runtime.previous_image = result.current_image
    runtime.is_initial_image = False

    if args.monitor:
        current_image = str(result.current_image) if result.current_image is not None else "(not copied)"
        print("generation:")
        if denoise_label is None:
            print(f"  mode={mode}")
        else:
            print(f"  mode={mode} denoise={denoise_label}")
        print(f"  prompt_id={result.prompt_id}")
        print(f"  comfy_output={result.comfy_filename}")
        print(f"  current_image={current_image}")
        print("timing:")
        print(f"  refine={refine_duration:.2f}s generation={generation_duration:.2f}s total={time.monotonic() - started_at:.2f}s")


def _format_chunk_timing(chunk: TranscriptChunk) -> str:
    if chunk.start is None:
        return ""

    if chunk.end is None:
        return f" [{chunk.start:05.2f}s]"

    return f" [{chunk.start:05.2f}s -> {chunk.end:05.2f}s]"


def _chunk_lag(
    chunk: TranscriptChunk,
    scheduled_start: float | None,
    delay_scale: float,
) -> float | None:
    if scheduled_start is None or chunk.start is None:
        return None

    scheduled_time = scheduled_start + (chunk.start * delay_scale)
    return time.monotonic() - scheduled_time


if __name__ == "__main__":
    main()
