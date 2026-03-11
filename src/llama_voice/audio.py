from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import logging
from pathlib import Path

log = logging.getLogger(__name__)


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
    try:
        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=True)
            return True
        if shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True)
            return True
        if shutil.which("pbcopy"):
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
            return True
    except Exception as exc:  # noqa: BLE001
        log.error("Clipboard copy failed: %s", exc)
    return False


def _type_with_xdotool(text: str) -> bool:
    xdotool = shutil.which("xdotool")
    if not xdotool:
        return False

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    for idx, line in enumerate(lines):
        if line:
            r = subprocess.run(
                [xdotool, "type", "--clearmodifiers", "--delay", "1", line],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if r.returncode != 0:
                return False
        if idx < len(lines) - 1:
            subprocess.run(
                [xdotool, "key", "--clearmodifiers", "Return"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    return True


def _type_with_wtype(text: str) -> bool:
    wtype = shutil.which("wtype")
    if not wtype:
        return False

    result = subprocess.run([wtype, text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def _applescript_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _type_with_osascript(text: str) -> bool:
    osascript = shutil.which("osascript")
    if not osascript:
        return False

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    cmd = [osascript, "-e", 'tell application "System Events"']
    for idx, line in enumerate(lines):
        escaped = _applescript_escape(line)
        cmd.extend(["-e", f'keystroke "{escaped}"'])
        if idx < len(lines) - 1:
            cmd.extend(["-e", "key code 36"])
    cmd.extend(["-e", "end tell"])
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def _type_with_ydotool(text: str) -> bool:
    ydotool = shutil.which("ydotool")
    # Also check common user-local path if not on PATH
    if not ydotool:
        candidate = Path.home() / ".local" / "bin" / "ydotool"
        if candidate.exists():
            ydotool = str(candidate)
    if not ydotool:
        return False
    _ensure_ydotoold()

    env = dict(os.environ)
    if "YDOTOOL_SOCKET" not in env:
        socket_candidates = [
            Path("/tmp/ydotool_socket"),
            Path.home() / ".ydotool_socket",
            Path("/run/ydotool_socket"),
        ]
        for candidate in socket_candidates:
            if candidate.exists():
                env["YDOTOOL_SOCKET"] = str(candidate)
                break

    result = subprocess.run(
        [ydotool, "type", "--key-delay", "0", text],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    if result.returncode != 0:
        log.error(
            "ydotool failed (rc=%d): %s", result.returncode, result.stderr.decode(errors="replace"),
        )
    return result.returncode == 0


def _type_with_pynput_paste() -> bool:
    try:
        from pynput.keyboard import Controller, Key
    except Exception:
        return False

    try:
        keyboard = Controller()
        keyboard.press(Key.ctrl)
        keyboard.press("v")
        keyboard.release("v")
        keyboard.release(Key.ctrl)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("pynput paste (Ctrl+V) failed: %s", exc)
        return False


def _type_with_pynput(text: str) -> bool:
    try:
        from pynput.keyboard import Controller
    except Exception:
        return False

    try:
        keyboard = Controller()
        keyboard.type(text)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("pynput typing failed: %s", exc)
        return False


def _ensure_ydotoold() -> None:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return

    is_active = subprocess.run(
        [systemctl, "--user", "is-active", "--quiet", "ydotoold.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if is_active.returncode == 0:
        return

    # Best-effort autostart. Keep it quiet in case the unit is unavailable.
    subprocess.run(
        [systemctl, "--user", "start", "ydotoold.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def _paste_from_clipboard(text: str) -> bool:
    if not copy_to_clipboard(text):
        log.debug("Clipboard copy failed for fallback paste")
        return False
    return _type_with_pynput_paste()


def type_into_active_app(text: str) -> bool:
    if not text:
        return False

    if sys.platform.startswith("linux"):
        if _type_with_ydotool(text):
            log.debug("Typed via ydotool")
            return True

        if os.environ.get("WAYLAND_DISPLAY"):
            if _type_with_wtype(text):
                log.debug("Typed via wtype (wayland)")
                return True
            if _type_with_pynput(text):
                log.debug("Typed via pynput (wayland)")
                return True
            if _paste_from_clipboard(text):
                log.debug("Typed via clipboard paste (wayland)")
                return True
            return False

        if _type_with_xdotool(text):
            log.debug("Typed via xdotool (x11)")
            return True
        if _type_with_ydotool(text):
            log.debug("Typed via ydotool (x11)")
            return True
        if _type_with_wtype(text):
            log.debug("Typed via wtype (x11)")
            return True
        if _type_with_pynput(text):
            log.debug("Typed via pynput (x11)")
            return True
        return False

    if sys.platform == "darwin":
        return _type_with_osascript(text)

    return False
