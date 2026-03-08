from llama_voice.config import (
    DEFAULT_BASE_URL,
    DEFAULT_STT_MODEL,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    normalize_base_url,
)


def test_normalize_base_url_adds_v1() -> None:
    assert normalize_base_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080/v1"


def test_normalize_base_url_keeps_v1() -> None:
    assert normalize_base_url("http://127.0.0.1:8080/v1/") == "http://127.0.0.1:8080/v1"


def test_defaults_are_performance_tuned() -> None:
    assert DEFAULT_STT_MODEL == "whisper-large-v3-turbo"
    assert DEFAULT_TTS_MODEL == "kokoro-82m"
    assert DEFAULT_TTS_VOICE == "af_sky"


def test_default_host_maps_to_lan_llama_swap() -> None:
    assert DEFAULT_BASE_URL == "http://192.168.0.101:8080"
