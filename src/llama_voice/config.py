from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE_URL = "http://192.168.0.101:8080"
DEFAULT_STT_MODEL = "whisper-large-v3-turbo"
DEFAULT_TTS_MODEL = "kokoro-82m"
DEFAULT_TTS_VOICE = "af_sky"
DEFAULT_STT_LANGUAGE = "en"
USER_CONFIG_PATH = Path.home() / ".config" / "llama-voice" / "config.env"


@dataclass(frozen=True)
class VoiceConfig:
    base_url: str
    api_key: str
    stt_model: str
    tts_model: str
    tts_voice: str
    stt_language: str



def normalize_base_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _first_csv(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    return value.split(",")[0].strip() or fallback


def _load_user_config(path: Path = USER_CONFIG_PATH) -> dict[str, str]:
    if not path.exists():
        return {}

    parsed: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def _read_value(name: str, user_conf: dict[str, str], default: str = "") -> str:
    return os.getenv(name) or user_conf.get(name, default)


def load_config(host_override: str | None = None) -> VoiceConfig:
    user_conf = _load_user_config()

    local_base_urls = _read_value("LOCAL_BASE_URLS", user_conf)
    ollama_base_urls = _read_value("OLLAMA_BASE_URLS", user_conf)

    base_raw = (
        host_override
        or _read_value("LLAMA_SWAP_BASE_URL", user_conf)
        or _first_csv(local_base_urls, "")
        or _first_csv(ollama_base_urls, "")
        or DEFAULT_BASE_URL
    )

    return VoiceConfig(
        base_url=normalize_base_url(base_raw),
        api_key=_read_value("LLAMA_SWAP_API_KEY", user_conf)
        or _read_value("OPENAI_API_KEY", user_conf),
        stt_model=_read_value("VOICE_STT_MODEL", user_conf, DEFAULT_STT_MODEL),
        tts_model=_read_value("VOICE_TTS_MODEL", user_conf, DEFAULT_TTS_MODEL),
        tts_voice=_read_value("VOICE_TTS_VOICE", user_conf, DEFAULT_TTS_VOICE),
        stt_language=_read_value("VOICE_STT_LANGUAGE", user_conf, DEFAULT_STT_LANGUAGE),
    )


def save_user_config(host: str, api_key: str | None = None, path: Path = USER_CONFIG_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# llama-voice user config",
        f"LLAMA_SWAP_BASE_URL={host}",
    ]

    if api_key:
        lines.append(f"LLAMA_SWAP_API_KEY={api_key}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
