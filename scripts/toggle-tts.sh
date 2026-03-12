#!/usr/bin/env bash
# Toggle TTS on/off. Sends a desktop notification with the new state.
FLAG="$HOME/.config/llama-voice/tts-disabled"

if [ -f "$FLAG" ]; then
  rm "$FLAG"
  notify-send -t 2000 "TTS Enabled" "Text-to-speech is now on" 2>/dev/null || true
else
  mkdir -p "$(dirname "$FLAG")"
  touch "$FLAG"
  # Also kill any currently playing TTS
  pkill -f 'ffplay.*-nodisp.*-autoexit' 2>/dev/null || true
  notify-send -t 2000 "TTS Disabled" "Text-to-speech is now off" 2>/dev/null || true
fi
