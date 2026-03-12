from __future__ import annotations

import argparse
import os
import signal
import sys
import tempfile
import time
from pathlib import Path

from .audio import AudioToolError, copy_to_clipboard, play_wav, play_wav_stream, start_recording_ffmpeg, stop_recording_ffmpeg
from .chunked_stt import ChunkedSTTSession, send_notification
from .client import LlamaSwapAudioClient
from .config import USER_CONFIG_PATH, load_config, save_user_config

SUBCOMMANDS = {"tts", "listen", "stt-file", "pair-laptop", "dictate", "toggle"}
PIDFILE = Path(tempfile.gettempdir()) / "llama-voice-dictate.pid"
HOTKEY_TOKEN_ALIASES = {
    "alt": "<alt>",
    "alt_l": "<alt_l>",
    "alt_r": "<alt_r>",
    "altgr": "<alt_gr>",
    "cmd": "<cmd>",
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "esc": "<esc>",
    "escape": "<esc>",
    "meta": "<cmd>",
    "shift": "<shift>",
    "space": "<space>",
    "super": "<cmd>",
    "win": "<cmd>",
}


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
    listen.add_argument(
        "--hotkey",
        default="f8",
        help="Hotkey (single key like f8, or combo like ctrl+alt+space)",
    )
    listen.add_argument("--copy", action="store_true", help="Batch mode: record all, transcribe once, copy to clipboard")
    listen.add_argument("--chunk-seconds", type=float, default=3.0, help="Chunk duration for streaming mode (default: 3.0)")
    listen.add_argument("--model", default=None, help="Override STT model")
    listen.add_argument("--language", default=None, help="Override STT language (default: en)")

    stt = subparsers.add_parser("stt-file", help="Transcribe an existing wav file")
    stt.add_argument("path", help="Path to wav file")
    stt.add_argument("--model", default=None, help="Override STT model")
    stt.add_argument("--language", default=None, help="Override STT language")

    dictate = subparsers.add_parser("dictate", help="Stream speech-to-text into active window (runs until killed)")
    dictate.add_argument("--chunk-seconds", type=float, default=3.0, help="Chunk duration (default: 3.0)")
    dictate.add_argument("--model", default=None, help="Override STT model")
    dictate.add_argument("--language", default=None, help="Override STT language (default: en)")

    subparsers.add_parser("toggle", help="Toggle dictation on/off (bind this to a global hotkey)")

    pair = subparsers.add_parser("pair-laptop", help="Persist host/API key for this laptop")
    pair.add_argument("--host", default="http://192.168.0.101:8080", help="Remote llama-swap host")
    pair.add_argument("--api-key", default="", help="Optional API key")

    return parser


def _resolve_hotkey(raw: str, keyboard):
    normalized = raw.strip().lower()
    if len(normalized) == 1:
        return normalized
    if hasattr(keyboard.Key, normalized):
        return getattr(keyboard.Key, normalized)
    raise ValueError(
        f"Unsupported hotkey '{raw}'. Use a single character or pynput key name like f8/f9/f10."
    )


def _is_combo_hotkey(raw: str) -> bool:
    normalized = raw.strip().lower()
    return "+" in normalized or normalized.count("-") >= 2


def _to_pynput_hotkey(raw: str) -> str:
    normalized = raw.strip().lower()
    splitter = "+" if "+" in normalized else "-"
    parts = [part.strip() for part in normalized.split(splitter) if part.strip()]
    if len(parts) < 2:
        raise ValueError(
            f"Invalid combo hotkey '{raw}'. Use format like ctrl+alt+space or ctrl-alt-space."
        )

    mapped_parts: list[str] = []
    for token in parts:
        mapped = HOTKEY_TOKEN_ALIASES.get(token)
        if mapped:
            mapped_parts.append(mapped)
            continue

        if len(token) == 1:
            mapped_parts.append(token)
            continue

        if token.startswith("f") and token[1:].isdigit():
            mapped_parts.append(f"<{token}>")
            continue

        if token.isidentifier():
            mapped_parts.append(f"<{token}>")
            continue

        raise ValueError(
            f"Unsupported combo token '{token}' in hotkey '{raw}'. "
            "Use keys like ctrl/alt/shift/space/f8/a."
        )

    return "+".join(mapped_parts)


def _matches_hotkey(key, target) -> bool:
    if isinstance(target, str):
        return getattr(key, "char", None) and key.char.lower() == target
    return key == target


def _run_tts(
    client: LlamaSwapAudioClient,
    text: str,
    voice: str | None,
    model: str | None,
    speed: float,
    output: str | None,
    no_play: bool,
) -> int:
    # Stream directly to ffplay when no file output is needed
    if not output and not no_play:
        chunks = client.synthesize_stream(text=text, voice=voice, model=model, speed=speed)
        play_wav_stream(chunks)
        return 0

    out_path = (
        Path(output)
        if output
        else Path(tempfile.gettempdir()) / f"llama-voice-tts-{int(time.time() * 1000)}.wav"
    )
    client.synthesize(text=text, output_wav=out_path, voice=voice, model=model, speed=speed)
    print(f"Generated: {out_path}")
    if not no_play:
        play_wav(out_path)
    return 0


def _run_stt_file(
    client: LlamaSwapAudioClient,
    wav_path: str,
    model: str | None,
    language: str | None,
) -> int:
    text = client.transcribe(Path(wav_path), model=model, language=language)
    print(text)
    return 0


def _run_pair_laptop(host: str, api_key: str) -> int:
    saved = save_user_config(host=host, api_key=api_key or None)
    print(f"Saved laptop mapping to: {saved}")
    print(f"llama-swap host: {host}")
    print('You can now run: llama-voice "hello from laptop"')
    return 0


def _run_hotkey_stt(
    client: LlamaSwapAudioClient,
    hotkey: str,
    copy: bool,
    chunk_seconds: float,
    model: str | None,
    language: str | None,
) -> int:
    try:
        from pynput import keyboard
    except Exception as exc:  # noqa: BLE001
        raise AudioToolError(
            "Hotkey mode requires an active desktop session (X11/Wayland) for pynput."
        ) from exc

    state = {
        "session": None,
        "recording_proc": None,
        "recording_file": None,
        "hotkey_down": False,
        "busy": False,
    }

    mode_label = "batch (--copy)" if copy else f"streaming ({chunk_seconds}s chunks)"
    print("Hotkey STT ready")
    print(f"Hotkey: {hotkey} | Mode: {mode_label}")
    print("Press hotkey to start, press again to stop. ESC to quit.")

    def toggle() -> None:
        if state["busy"]:
            return

        if copy:
            if state["recording_proc"] is None:
                wav_path = Path(tempfile.gettempdir()) / f"llama-voice-stt-{int(time.time() * 1000)}.wav"
                state["recording_file"] = wav_path
                state["recording_proc"] = start_recording_ffmpeg(wav_path)
                print("Recording...")
                return

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
                return

            did_copy = copy_to_clipboard(text)
            print("(copied)" if did_copy else "(clipboard tool not found)")
            print(text)
            print("---")
            state["busy"] = False
        else:
            if state["session"] is None:
                session = ChunkedSTTSession(
                    client, model=model, language=language, chunk_seconds=chunk_seconds,
                )
                state["session"] = session
                session.start()
            else:
                state["busy"] = True
                state["session"].stop()
                state["session"] = None
                state["busy"] = False

    if _is_combo_hotkey(hotkey):
        try:
            parsed_combo = keyboard.HotKey.parse(_to_pynput_hotkey(hotkey))
        except Exception as exc:  # noqa: BLE001
            raise AudioToolError(str(exc)) from exc

        combo = keyboard.HotKey(parsed_combo, toggle)
        listener = None

        def on_press(key):
            if key == keyboard.Key.esc:
                return False
            combo.press(listener.canonical(key))
            return None

        def on_release(key):
            combo.release(listener.canonical(key))
            return None

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    else:
        target = _resolve_hotkey(hotkey, keyboard)

        def on_press(key):
            if key == keyboard.Key.esc:
                return False
            if state["hotkey_down"]:
                return None
            if _matches_hotkey(key, target):
                state["hotkey_down"] = True
                toggle()
            return None

        def on_release(key):
            if _matches_hotkey(key, target):
                state["hotkey_down"] = False
            return None

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    if state["session"] is not None:
        state["session"].stop()
    if state["recording_proc"] is not None:
        stop_recording_ffmpeg(state["recording_proc"])

    return 0


def _start_noise_filter() -> None:
    import subprocess
    subprocess.run(
        ["systemctl", "--user", "start", "filter-chain.service"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _stop_noise_filter() -> None:
    import subprocess
    subprocess.run(
        ["systemctl", "--user", "stop", "filter-chain.service"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _run_dictate(
    client: LlamaSwapAudioClient,
    chunk_seconds: float,
    model: str | None,
    language: str | None,
) -> int:
    _start_noise_filter()
    session = ChunkedSTTSession(client, model=model, language=language, chunk_seconds=chunk_seconds)

    def _shutdown(signum, frame):  # noqa: ARG001
        session.stop()
        _stop_noise_filter()
        PIDFILE.unlink(missing_ok=True)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    PIDFILE.write_text(str(os.getpid()))
    try:
        session.start()
        # Block until signaled
        signal.pause()
    finally:
        _stop_noise_filter()
        PIDFILE.unlink(missing_ok=True)
    return 0


def _run_toggle() -> int:
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            send_notification("Dictation stopped")
            return 0
        except (ProcessLookupError, ValueError):
            # Stale pidfile
            PIDFILE.unlink(missing_ok=True)

    # No running instance — start one in the background
    import subprocess

    venv_bin = Path(sys.executable).parent
    llama_voice = venv_bin / "llama-voice"
    if not llama_voice.exists():
        llama_voice = Path("llama-voice")  # fall back to PATH

    subprocess.Popen(
        [str(llama_voice), "dictate"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return 0


def _extract_direct_tts(argv_tokens: list[str]) -> tuple[str | None, str | None]:
    if not argv_tokens:
        return None, None

    host_override: str | None = None
    tokens = list(argv_tokens)

    if len(tokens) >= 2 and tokens[0] == "--host":
        host_override = tokens[1]
        tokens = tokens[2:]

    if not tokens:
        return None, host_override

    first = tokens[0]
    if first in SUBCOMMANDS or first.startswith("-"):
        return None, host_override

    return " ".join(tokens), host_override


def main(argv: list[str] | None = None) -> int:
    argv_tokens = list(argv) if argv is not None else sys.argv[1:]

    direct_text, direct_host = _extract_direct_tts(argv_tokens)
    if direct_text:
        cfg = load_config(host_override=direct_host)
        client = LlamaSwapAudioClient(cfg)
        try:
            return _run_tts(
                client,
                text=direct_text,
                voice=None,
                model=None,
                speed=1.0,
                output=None,
                no_play=False,
            )
        except AudioToolError as exc:
            print(f"Audio setup error: {exc}")
            return 2
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            return 1

    parser = _build_parser()
    args = parser.parse_args(argv_tokens)

    if args.command == "pair-laptop":
        return _run_pair_laptop(host=args.host, api_key=args.api_key)

    if args.command == "toggle":
        return _run_toggle()

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

        if args.command == "dictate":
            return _run_dictate(
                client,
                chunk_seconds=args.chunk_seconds,
                model=args.model,
                language=args.language,
            )

        if args.command == "listen":
            return _run_hotkey_stt(
                client,
                hotkey=args.hotkey,
                copy=args.copy,
                chunk_seconds=args.chunk_seconds,
                model=args.model,
                language=args.language,
            )

        if args.command == "stt-file":
            return _run_stt_file(client, args.path, model=args.model, language=args.language)

        parser.print_help()
        print(f"\nConfig file path: {USER_CONFIG_PATH}")
        print('Direct TTS shortcut: llama-voice "hello world"')
        return 0

    except AudioToolError as exc:
        print(f"Audio setup error: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
