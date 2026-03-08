from __future__ import annotations

import shutil
import signal
import subprocess
import sys
from pathlib import Path


class AudioToolError(RuntimeError):
    pass


def _require_binary(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise AudioToolError(f"Required binary not found: {name}")
    return binary


def start_recording_ffmpeg(out_wav: Path, sample_rate: int = 16000) -> subprocess.Popen[bytes]:
    ffmpeg = _require_binary("ffmpeg")

    if sys.platform.startswith("linux"):
        args = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "pulse",
            "-i",
            "default",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ]
    elif sys.platform == "darwin":
        args = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "avfoundation",
            "-i",
            ":0",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ]
    else:
        raise AudioToolError(f"Unsupported platform for default recorder setup: {sys.platform}")

    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def stop_recording_ffmpeg(proc: subprocess.Popen[bytes], timeout_seconds: float = 5.0) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


def play_wav(wav_path: Path) -> None:
    ffplay = shutil.which("ffplay")
    if ffplay:
        subprocess.run(
            [ffplay, "-nodisp", "-autoexit", "-loglevel", "error", str(wav_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    aplay = shutil.which("aplay")
    if aplay:
        subprocess.run([aplay, str(wav_path)], check=True)
        return

    afplay = shutil.which("afplay")
    if afplay:
        subprocess.run([afplay, str(wav_path)], check=True)
        return

    raise AudioToolError("No playback binary found (ffplay/aplay/afplay)")


def copy_to_clipboard(text: str) -> bool:
    if shutil.which("wl-copy"):
        subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=True)
        return True
    if shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True)
        return True
    if shutil.which("pbcopy"):
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    return False
