from __future__ import annotations

from pathlib import Path

import requests

from .config import VoiceConfig


class LlamaSwapAudioClient:
    def __init__(self, config: VoiceConfig, timeout_seconds: int = 120) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def transcribe(self, wav_path: Path, model: str | None = None, language: str | None = None) -> str:
        url = f"{self.config.base_url}/audio/transcriptions"
        data = {
            "model": model or self.config.stt_model,
            "language": language or self.config.stt_language,
            "temperature": "0",
        }
        with wav_path.open("rb") as audio_file:
            files = {"file": (wav_path.name, audio_file, "audio/wav")}
            response = requests.post(
                url,
                headers=self._headers(),
                data=data,
                files=files,
                timeout=self.timeout_seconds,
            )

        response.raise_for_status()
        payload = response.json()
        text = payload.get("text")
        if not isinstance(text, str):
            raise RuntimeError(f"Unexpected STT response payload: {payload}")
        return text.strip()

    def synthesize(
        self,
        text: str,
        output_wav: Path,
        model: str | None = None,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> Path:
        if not text.strip():
            raise ValueError("TTS text is empty")

        url = f"{self.config.base_url}/audio/speech"
        payload = {
            "model": model or self.config.tts_model,
            "voice": voice or self.config.tts_voice,
            "input": text,
            "response_format": "wav",
            "speed": speed,
        }

        response = requests.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        output_wav.write_bytes(response.content)
        return output_wav
