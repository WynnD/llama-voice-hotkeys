#!/usr/bin/env bash
# Read highlighted text aloud via TTS (bind to a global hotkey)
set -euo pipefail

# Kill any running TTS audio playback
pkill -f 'ffplay.*-nodisp.*-autoexit' 2>/dev/null || true

TEXT=$(wl-paste --primary 2>/dev/null || true)

[ -z "$TEXT" ] && exit 0

# Truncate very long selections
if [ ${#TEXT} -gt 5000 ]; then
  TEXT="${TEXT:0:5000}..."
fi

~/projects/llama-voice-hotkeys/.venv/bin/llama-voice "$TEXT"
