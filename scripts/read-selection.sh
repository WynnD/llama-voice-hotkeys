#!/usr/bin/env bash
# Read highlighted text aloud via TTS (bind to a global hotkey)
set -euo pipefail

# Skip if TTS is toggled off
[ -f "$HOME/.config/llama-voice/tts-disabled" ] && exit 0

# Kill any running TTS audio playback
pkill -f 'ffplay.*-nodisp.*-autoexit' 2>/dev/null || true

TEXT=$(wl-paste --primary 2>/dev/null || true)

[ -z "$TEXT" ] && exit 0

# Truncate very long selections
if [ ${#TEXT} -gt 5000 ]; then
  TEXT="${TEXT:0:5000}..."
fi

# Space out ticket IDs (e.g. BEA-543 → B E A 5 4 3) so TTS reads them clearly
TEXT=$(echo "$TEXT" | sed -E 's/\b([A-Z]{1,3})-([0-9]{1,5})\b/\1 \2/g' | sed -E 's/\b([A-Z])([A-Z])([A-Z])\b/\1 \2 \3/g; s/\b([A-Z])([A-Z])\b/\1 \2/g' | sed -E 's/([A-Z]) ([0-9])([0-9])([0-9])([0-9])([0-9])\b/\1 \2 \3 \4 \5 \6/g; s/([A-Z]) ([0-9])([0-9])([0-9])([0-9])\b/\1 \2 \3 \4 \5/g; s/([A-Z]) ([0-9])([0-9])([0-9])\b/\1 \2 \3 \4/g; s/([A-Z]) ([0-9])([0-9])\b/\1 \2 \3/g')

~/projects/llama-voice-hotkeys/.venv/bin/llama-voice "$TEXT"
