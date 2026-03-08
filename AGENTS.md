# AGENTS

## Voice Workflow

Use `llama-voice` for local speech I/O through llama-swap.

Default mapped host: `http://192.168.0.101:8080`

## Laptop Setup

Run once on laptop:

```bash
llama-voice pair-laptop --host http://192.168.0.101:8080
```

This persists mapping at `~/.config/llama-voice/config.env`.

## STT (hotkey)

```bash
llama-voice listen --hotkey f8 --copy
```

- press hotkey once to start recording
- press hotkey again to stop and transcribe
- press `Esc` to quit

## TTS (command-triggered)

```bash
llama-voice "output text to here to talk"
# or
llama-voice tts "output text to here to talk"
```

## Model defaults (speed + quality)

- STT: `whisper-large-v3-turbo`
- TTS: `kokoro-82m`
- Voice: `af_sky`

## Streaming note

- TTS backend supports streaming via llama-swap API (`/v1/audio/speech`, `"stream": true`).
- CLI currently writes returned audio to WAV and then plays it.
- STT endpoint is request/response (`/v1/audio/transcriptions`).

## Runtime note

- Hotkey mode requires an active desktop session (X11/Wayland).
- `tts` and `stt-file` can run in headless sessions.

Override with env vars:

```bash
export VOICE_STT_MODEL="..."
export VOICE_TTS_MODEL="..."
export VOICE_TTS_VOICE="..."
```
