# llama-voice

Talk to your local AI models using simple commands.

`llama-voice` gives you:
- Hotkey speech-to-text (STT)
- Text-to-speech (TTS) from a single command
- Laptop-to-desktop mapping to your llama-swap server (`192.168.0.101:8080`)

## What You Can Do

- Say something and get text back quickly
- Turn text into spoken audio quickly
- Run from laptop while using models hosted on your desktop

## 1) Install

```bash
cd ~/projects/llama-voice-hotkeys
uv venv --clear .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

## 2) Pair Your Laptop (One Time)

This tells the CLI to always use your desktop llama-swap host.

```bash
llama-voice pair-laptop --host http://192.168.0.101:8080
```

It saves your mapping here:
- `~/.config/llama-voice/config.env`

## 3) Use It

### Talk from text (TTS)

```bash
llama-voice "output text to here to talk"
# or
llama-voice tts "output text to here to talk"
```

### Start hotkey transcription (STT)

```bash
llama-voice listen --hotkey f8
```

Behavior:
- Press `F8` once: start recording
- Press `F8` again: stop + type into active app
- Press `Esc`: quit

If you bind this to a GNOME shortcut, the command should be `llama-voice listen ...` and the GNOME shortcut key should be different from the internal `--hotkey` value.

For a true one-key workflow in GNOME, use:

```bash
# Toggle background dictate (start/stop stream typing)
llama-voice toggle
```

Recommended GNOME setup (run this in your GNOME session):

```bash
./scripts/setup_gnome_voice_hotkey.sh '<Primary><Alt>space>'
```

### Start hotkey transcription (copy mode)

```bash
llama-voice listen --hotkey f8 --copy
```

Behavior:
- Press `F8` once: start recording
- Press `F8` again: stop + transcribe
- Press `Esc`: quit
- `--copy` copies transcript to clipboard and does not type into the app

### Transcribe a WAV file

```bash
llama-voice stt-file ./sample.wav
```

## 4) Model Defaults (Fast + High Quality)

- STT model: `whisper-large-v3-turbo`
- TTS model: `kokoro-82m`
- Voice: `af_sky`

You can override anytime:

```bash
export VOICE_STT_MODEL="whisper-large-v3-turbo"
export VOICE_TTS_MODEL="kokoro-82m"
export VOICE_TTS_VOICE="af_sky"
```

## 5) If You Need a Different Host

One command only:

```bash
llama-voice --host http://YOUR-HOST:8080 "hello"
```

Or set permanently:

```bash
export LLAMA_SWAP_BASE_URL="http://YOUR-HOST:8080"
```

## 6) Streaming Note

- TTS backend (`kokoro-82m`) supports streaming over llama-swap (`/v1/audio/speech` with `"stream": true`).
- Current CLI playback path writes returned audio to WAV then plays it.
- STT path is standard request/response (`/v1/audio/transcriptions`), not partial live transcript streaming.

## Requirements

### Required

- `ffmpeg` (recording)
- One playback tool: `ffplay` or `aplay` or `afplay`

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### Runtime notes

- `listen` hotkey mode needs an active desktop session (X11/Wayland).
- `tts` and `stt-file` work in headless/SSH-only sessions.

### Optional

Clipboard support for `--copy`:
- Linux Wayland: `wl-copy`
- Linux X11: `xclip`
- macOS: `pbcopy` (already included)

## Quick Health Check

From your laptop, verify your desktop host is reachable:

```bash
curl http://192.168.0.101:8080/v1/models
```

Direct API checks:

```bash
# STT
curl -sS -X POST http://192.168.0.101:8080/v1/audio/transcriptions \
  -F model=whisper-large-v3-turbo \
  -F file=@./sample.wav

# TTS (streaming)
curl -sS -X POST http://192.168.0.101:8080/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"model":"kokoro-82m","voice":"af_sky","input":"hello","stream":true}' \
  > /tmp/tts-stream.bin
```

If connectivity fails:
- Ensure laptop and desktop are on same LAN/VPN
- Ensure llama-swap is running on desktop
- Ensure port `8080` is reachable

## Everyday Commands

```bash
# Activate env
source ~/projects/llama-voice-hotkeys/.venv/bin/activate

# Speak text
llama-voice "meeting starts in 5 minutes"

# Dictate text with hotkey
llama-voice listen --hotkey f8 --copy

# GNOME-friendly one-key setup
llama-voice toggle
```
