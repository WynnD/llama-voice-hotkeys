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
```

## Defaults

- STT model: `whisper-large-v3-turbo`
- TTS model: `kokoro-82m`
- TTS voice: `af_sky`

## Override models

```bash
export VOICE_STT_MODEL="..."
export VOICE_TTS_MODEL="..."
export VOICE_TTS_VOICE="..."
```
