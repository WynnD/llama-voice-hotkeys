"""Chunked streaming STT — records in short segments, transcribes each, types results live."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .audio import AudioToolError, start_recording_ffmpeg, stop_recording_ffmpeg, type_into_active_app
from .client import LlamaSwapAudioClient

# Common whisper hallucinations on silence
HALLUCINATIONS = {
    "thank you.", "thank you", "thanks.", "thanks",
    "thank you for watching.", "thank you for watching",
    "thanks for watching.", "thanks for watching",
    "you", "bye.", "bye",
    "the end.", "the end",
    "so,", "so.",
    "okay.", "okay",
    "...",
}

LOG_PATH = Path(tempfile.gettempdir()) / "llama-voice-dictate.log"
logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def send_notification(title: str, body: str = "", timeout_ms: int = 2000) -> None:
    notify = shutil.which("notify-send")
    if notify:
        subprocess.Popen(
            [notify, "-t", str(timeout_ms), title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class ChunkedSTTSession:
    def __init__(
        self,
        client: LlamaSwapAudioClient,
        model: str | None = None,
        language: str | None = None,
        chunk_seconds: float = 3.0,
    ) -> None:
        self.client = client
        self.model = model
        self.language = language
        self.chunk_seconds = chunk_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        # Ensure ydotool can find its socket when spawned from GNOME
        os.environ.setdefault("YDOTOOL_SOCKET", str(Path.home() / ".ydotool_socket"))
        log.info("Dictation starting (chunk=%.1fs)", self.chunk_seconds)
        send_notification("Listening...", "Speak now")
        print("Recording — speak now. Press hotkey again to stop.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)
        send_notification("Done", "Dictation complete")
        print("\nDictation complete.")

    def _next_chunk_path(self) -> Path:
        return Path(tempfile.gettempdir()) / f"llama-voice-chunk-{int(time.time() * 1000)}.wav"

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            chunk_path = self._next_chunk_path()
            try:
                proc = start_recording_ffmpeg(chunk_path)
            except AudioToolError as exc:
                log.error("Recording error: %s", exc)
                return

            self._stop_event.wait(timeout=self.chunk_seconds)
            stop_recording_ffmpeg(proc)

            if chunk_path.exists() and chunk_path.stat().st_size > 44:
                try:
                    text = self.client.transcribe(chunk_path, model=self.model, language=self.language)
                    log.debug("Transcribed: %r", text)
                except Exception as exc:  # noqa: BLE001
                    log.error("Transcription error: %s", exc)
                    chunk_path.unlink(missing_ok=True)
                    continue

                if text and text.strip().lower() not in HALLUCINATIONS:
                    typed = type_into_active_app(text + " ")
                    log.debug("Typed=%s text=%r", typed, text)
                    if not typed:
                        print(text, end=" ", flush=True)
                elif text:
                    log.debug("Filtered hallucination: %r", text)
            else:
                log.debug("Chunk too small, skipping: %s", chunk_path)

            chunk_path.unlink(missing_ok=True)
        log.info("Run loop exiting")
