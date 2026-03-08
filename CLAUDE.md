# CLAUDE

## Speech Commands

CLI name: `llama-voice`

## Host Mapping

Default host is `http://192.168.0.101:8080`.

Pair a laptop once:

```bash
llama-voice pair-laptop --host http://192.168.0.101:8080
```

This writes `~/.config/llama-voice/config.env`.

## Hotkey STT

```bash
llama-voice listen --hotkey f8 --copy
```

## TTS (direct command)

```bash
llama-voice "output text to here to talk"
# or
llama-voice tts "output text to here to talk"
```

## Defaults

- STT model: `whisper-large-v3-turbo`
- TTS model: `kokoro-82m`
- TTS voice: `af_sky`

## Streaming note

- TTS supports streaming at API level (`/v1/audio/speech` with `"stream": true`).
- CLI writes returned audio to WAV then plays it.
- STT endpoint is `/v1/audio/transcriptions`.

## Runtime note

- Hotkey mode requires an active desktop session (X11/Wayland).
- `tts` and `stt-file` can run in headless sessions.

## Override models

```bash
export VOICE_STT_MODEL="..."
export VOICE_TTS_MODEL="..."
export VOICE_TTS_VOICE="..."
```
