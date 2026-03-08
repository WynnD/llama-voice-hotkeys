from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from pynput import keyboard

from .audio import AudioToolError, copy_to_clipboard, play_wav, start_recording_ffmpeg, stop_recording_ffmpeg
from .client import LlamaSwapAudioClient
from .config import USER_CONFIG_PATH, load_config, save_user_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llama-voice",
        description="Hotkey STT + fast TTS for local llama-swap services",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Override llama-swap base URL for this run (ex: http://192.168.0.101:8080)",
    )

    subparsers = parser.add_subparsers(dest="command")

    tts = subparsers.add_parser("tts", help="Speak text")
    tts.add_argument("text", nargs="+", help="Text to speak")
    tts.add_argument("--voice", default=None, help="Override TTS voice")
    tts.add_argument("--model", default=None, help="Override TTS model")
    tts.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    tts.add_argument("--output", default=None, help="Save wav output to this path")
    tts.add_argument("--no-play", action="store_true", help="Do not auto-play generated wav")

    listen = subparsers.add_parser("listen", help="Global hotkey STT mode")
    listen.add_argument("--hotkey", default="f8", help="Single key hotkey (default: f8)")
    listen.add_argument("--copy", action="store_true", help="Copy transcript to clipboard")
    listen.add_argument("--model", default=None, help="Override STT model")
    listen.add_argument("--language", default=None, help="Override STT language (default: en)")

    stt = subparsers.add_parser("stt-file", help="Transcribe an existing wav file")
    stt.add_argument("path", help="Path to wav file")
    stt.add_argument("--model", default=None, help="Override STT model")
    stt.add_argument("--language", default=None, help="Override STT language")

    pair = subparsers.add_parser("pair-laptop", help="Persist host/API key for this laptop")
    pair.add_argument("--host", default="http://192.168.0.101:8080", help="Remote llama-swap host")
    pair.add_argument("--api-key", default="", help="Optional API key")

    parser.add_argument(
        "text",
        nargs="*",
        help='If provided without a subcommand, runs TTS directly: llama-voice "hello"',
    )
    return parser


def _resolve_hotkey(raw: str):
    normalized = raw.strip().lower()
    if len(normalized) == 1:
        return normalized
    if hasattr(keyboard.Key, normalized):
        return getattr(keyboard.Key, normalized)
    raise ValueError(
        f"Unsupported hotkey '{raw}'. Use a single character or pynput key name like f8/f9/f10."
    )


def _matches_hotkey(key, target) -> bool:
    if isinstance(target, str):
        return getattr(key, "char", None) and key.char.lower() == target
    return key == target


def _run_tts(client: LlamaSwapAudioClient, text: str, voice: str | None, model: str | None, speed: float, output: str | None, no_play: bool) -> int:
    out_path = Path(output) if output else Path(tempfile.gettempdir()) / f"llama-voice-tts-{int(time.time() * 1000)}.wav"
    client.synthesize(text=text, output_wav=out_path, voice=voice, model=model, speed=speed)
    print(f"Generated: {out_path}")
    if not no_play:
        play_wav(out_path)
    return 0


def _run_stt_file(client: LlamaSwapAudioClient, wav_path: str, model: str | None, language: str | None) -> int:
    text = client.transcribe(Path(wav_path), model=model, language=language)
    print(text)
    return 0


def _run_pair_laptop(host: str, api_key: str) -> int:
    saved = save_user_config(host=host, api_key=api_key or None)
    print(f"Saved laptop mapping to: {saved}")
    print(f"llama-swap host: {host}")
    print("You can now run: llama-voice \"hello from laptop\"")
    return 0


def _run_hotkey_stt(client: LlamaSwapAudioClient, hotkey: str, copy: bool, model: str | None, language: str | None) -> int:
    target = _resolve_hotkey(hotkey)
    state = {
        "recording_proc": None,
        "recording_file": None,
        "hotkey_down": False,
        "busy": False,
    }

    print("Hotkey STT ready")
    print(f"Hotkey: {hotkey}")
    print("Press hotkey once to start recording, press again to stop + transcribe.")
    print("Press ESC to quit.")

    def on_press(key):
        if key == keyboard.Key.esc:
            return False

        if state["hotkey_down"]:
            return None

        if _matches_hotkey(key, target):
            state["hotkey_down"] = True
            if state["busy"]:
                return None

            if state["recording_proc"] is None:
                wav_path = Path(tempfile.gettempdir()) / f"llama-voice-stt-{int(time.time() * 1000)}.wav"
                state["recording_file"] = wav_path
                state["recording_proc"] = start_recording_ffmpeg(wav_path)
                print("Recording...")
            else:
                state["busy"] = True
                proc = state["recording_proc"]
                wav_path = state["recording_file"]
                state["recording_proc"] = None
                state["recording_file"] = None
                stop_recording_ffmpeg(proc)
                print("Transcribing...")
                try:
                    text = client.transcribe(wav_path, model=model, language=language)
                except Exception as exc:  # noqa: BLE001
                    print(f"STT error: {exc}")
                    state["busy"] = False
                    return None

                if copy:
                    did_copy = copy_to_clipboard(text)
                    if did_copy:
                        print("(copied to clipboard)")
                    else:
                        print("(clipboard tool not found)")

                print(text)
                print("---")
                state["busy"] = False

        return None

    def on_release(key):
        if _matches_hotkey(key, target):
            state["hotkey_down"] = False

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    if state["recording_proc"] is not None:
        stop_recording_ffmpeg(state["recording_proc"])

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "pair-laptop":
        return _run_pair_laptop(host=args.host, api_key=args.api_key)

    cfg = load_config(host_override=args.host)
    client = LlamaSwapAudioClient(cfg)

    try:
        if args.command == "tts":
            return _run_tts(
                client,
                text=" ".join(args.text),
                voice=args.voice,
                model=args.model,
                speed=args.speed,
                output=args.output,
                no_play=args.no_play,
            )

        if args.command == "listen":
            return _run_hotkey_stt(
                client,
                hotkey=args.hotkey,
                copy=args.copy,
                model=args.model,
                language=args.language,
            )

        if args.command == "stt-file":
            return _run_stt_file(client, args.path, model=args.model, language=args.language)

        if args.text:
            return _run_tts(
                client,
                text=" ".join(args.text),
                voice=None,
                model=None,
                speed=1.0,
                output=None,
                no_play=False,
            )

        parser.print_help()
        print(f"\nConfig file path: {USER_CONFIG_PATH}")
        return 0

    except AudioToolError as exc:
        print(f"Audio setup error: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
