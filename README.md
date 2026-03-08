# llama-voice

Fast local speech CLI for llama-swap:
- Hotkey STT (press hotkey to start/stop recording and transcribe)
- Command-driven TTS (`llama-voice "text to speak"`)

Built for speed + quality with default models:
- STT: `whisper-large-v3-turbo` (high accuracy, fast)
- TTS: `kokoro-82m` + `af_sky` voice (high quality, fast)

Default host is mapped to your llama-swap machine:
- `http://192.168.0.101:8080`

## Install with uv

```bash
cd ~/projects/llama-voice-hotkeys
uv venv --clear .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

## Laptop pairing (one-time)

On your laptop, run:

```bash
llama-voice pair-laptop --host http://192.168.0.101:8080
```

This writes `~/.config/llama-voice/config.env`, so all future commands use your remote llama-swap automatically.

## Configure (optional overrides)

```bash
export LLAMA_SWAP_BASE_URL="http://192.168.0.101:8080"
export LLAMA_SWAP_API_KEY=""
export VOICE_STT_MODEL="whisper-large-v3-turbo"
export VOICE_TTS_MODEL="kokoro-82m"
export VOICE_TTS_VOICE="af_sky"
```

`LLAMA_SWAP_BASE_URL` can be set with or without `/v1`; the CLI normalizes it.

## Usage

```bash
# TTS shortcut mode (requested command shape)
llama-voice "output text to here to talk"

# Explicit TTS
llama-voice tts "Read this out loud"

# Hotkey STT mode (global listener)
llama-voice listen --hotkey f8 --copy

# Transcribe an existing wav file
llama-voice stt-file ./sample.wav

# One-off host override
llama-voice --host http://192.168.0.101:8080 "hello"
```

Hotkey mode behavior:
- Press hotkey once: start recording
- Press hotkey again: stop recording + transcribe
- Press `Esc`: quit

## System dependencies

Required binaries:
- `ffmpeg` for microphone capture
- one of `ffplay`, `aplay`, or `afplay` for audio playback

Optional binaries:
- `wl-copy` or `xclip` or `pbcopy` for `--copy`

## Network notes for laptop use

- Laptop must be on the same LAN/VPN as `192.168.0.101`
- Ensure inbound TCP `8080` is reachable on that machine
- If unreachable, test from laptop: `curl http://192.168.0.101:8080/v1/models`
