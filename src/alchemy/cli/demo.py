import argparse
from pathlib import Path
import sys

from alchemy.cli import from_audio
from alchemy.config import load_settings
from alchemy.services import run_checks


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Run the standard Alchemy demo pipeline.")
    parser.add_argument("audio_path", type=Path, nargs="?", help="Audio file to process.")
    parser.add_argument("--mic", action="store_true", help="Use live microphone input.")
    parser.add_argument(
        "--phrase-seconds",
        type=float,
        default=settings.alchemy_chunk_max_seconds,
        help="Microphone phrase window duration.",
    )
    parser.add_argument("--sample-rate", type=int, default=16000, help="Microphone sample rate.")
    parser.add_argument("--device", help="sounddevice input device name or index.")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit.")
    parser.add_argument("--skip-doctor", action="store_true", help="Skip service checks before running.")
    parser.add_argument("--no-monitor", action="store_true", help="Disable rehearsal monitor output.")
    parser.add_argument("--no-feedback", action="store_true", help="Disable img2img feedback.")
    parser.add_argument("--no-realtime", action="store_true", help="Run chunks as fast as possible.")
    parser.add_argument("--no-audio", action="store_true", help="Do not play the source audio.")
    parser.add_argument("--audio-player", help="Audio player command.")
    parser.add_argument("--backpressure", choices=("serial", "latest"), default=settings.alchemy_backpressure_mode)
    parser.add_argument("--delay-scale", type=float, default=settings.alchemy_delay_scale)
    parser.add_argument("--max-words", type=int, help="Chunk max word count override.")
    parser.add_argument("--max-seconds", type=float, help="Chunk max duration override.")
    parser.add_argument("--denoise", type=float, help="Override img2img denoise strength.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    if args.list_devices:
        from alchemy.cli import from_mic

        old_argv = sys.argv
        try:
            sys.argv = ["alchemy-from-mic", "--list-devices"]
            from_mic.main()
        finally:
            sys.argv = old_argv
        return

    if args.mic:
        _run_mic_demo(args, settings)
        return

    if args.audio_path is None:
        raise SystemExit("audio_path is required unless --mic is passed.")

    if not args.audio_path.exists():
        raise SystemExit(f"Audio file does not exist: {args.audio_path}")

    if not args.skip_doctor:
        checks = run_checks(settings)
        failed = [check for check in checks if not check.ok]
        for check in checks:
            status = "OK" if check.ok else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
            if check.fix:
                print(f"      Fix: {check.fix}")
        if failed:
            raise SystemExit(1)
        print()

    viewer_url = f"http://{settings.alchemy_viewer_host}:{settings.alchemy_viewer_port}"
    print("Demo mode")
    print(f"  viewer: {viewer_url}")
    print(f"  audio: {args.audio_path}")
    print("  path: chunked audio -> prompt refinement -> image generation")
    print()

    from_audio_args = [
        "alchemy-from-audio",
        "--chunked",
        str(args.audio_path),
        "--backpressure",
        args.backpressure,
        "--delay-scale",
        str(args.delay_scale),
    ]

    if not args.no_feedback:
        from_audio_args.append("--feedback")
    if not args.no_realtime:
        from_audio_args.append("--realtime")
    if not args.no_audio and not args.no_realtime:
        from_audio_args.append("--play-audio")
    if not args.no_monitor:
        from_audio_args.append("--monitor")
    if args.audio_player is not None:
        from_audio_args.extend(["--audio-player", args.audio_player])
    if args.max_words is not None:
        from_audio_args.extend(["--max-words", str(args.max_words)])
    if args.max_seconds is not None:
        from_audio_args.extend(["--max-seconds", str(args.max_seconds)])
    if args.denoise is not None:
        from_audio_args.extend(["--denoise", str(args.denoise)])

    old_argv = sys.argv
    try:
        sys.argv = from_audio_args
        from_audio.main()
    finally:
        sys.argv = old_argv


def _run_mic_demo(args: argparse.Namespace, settings) -> None:
    if not args.skip_doctor:
        checks = run_checks(settings)
        failed = [check for check in checks if not check.ok]
        for check in checks:
            status = "OK" if check.ok else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
            if check.fix:
                print(f"      Fix: {check.fix}")
        if failed:
            raise SystemExit(1)
        print()

    viewer_url = f"http://{settings.alchemy_viewer_host}:{settings.alchemy_viewer_port}"
    print("Demo mode")
    print(f"  viewer: {viewer_url}")
    print("  audio: microphone")
    print("  path: microphone phrases -> prompt refinement -> image generation")
    print()

    from alchemy.cli import from_mic

    from_mic_args = [
        "alchemy-from-mic",
        "--phrase-seconds",
        str(args.phrase_seconds),
        "--sample-rate",
        str(args.sample_rate),
        "--backpressure",
        args.backpressure,
    ]

    if not args.no_feedback:
        from_mic_args.append("--feedback")
    if not args.no_monitor:
        from_mic_args.append("--monitor")
    if args.device is not None:
        from_mic_args.extend(["--device", args.device])
    if args.list_devices:
        from_mic_args.append("--list-devices")
    if args.max_words is not None:
        from_mic_args.extend(["--max-words", str(args.max_words)])
    if args.max_seconds is not None:
        from_mic_args.extend(["--max-seconds", str(args.max_seconds)])
    if args.denoise is not None:
        from_mic_args.extend(["--denoise", str(args.denoise)])

    old_argv = sys.argv
    try:
        sys.argv = from_mic_args
        from_mic.main()
    finally:
        sys.argv = old_argv
