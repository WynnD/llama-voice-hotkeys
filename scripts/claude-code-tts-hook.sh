#!/usr/bin/env bash
# Claude Code Stop hook: speak the assistant's last message via TTS
set -euo pipefail

INPUT=$(cat)

# Skip if TTS is toggled off
[ -f "$HOME/.config/llama-voice/tts-disabled" ] && exit 0

# Kill any running TTS audio playback
pkill -f 'ffplay.*-nodisp.*-autoexit' 2>/dev/null || true

# Don't TTS if this is a stop-hook continuation (prevent loops)
if echo "$INPUT" | jq -e '.stop_hook_active == true' >/dev/null 2>&1; then
  exit 0
fi

MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')

# Skip if empty
[ -z "$MSG" ] && exit 0

# Truncate very long messages for TTS
if [ ${#MSG} -gt 2000 ]; then
  MSG="${MSG:0:2000}..."
fi

# Strip markdown formatting for cleaner speech
MSG=$(echo "$MSG" | sed -E 's/```[^`]*```//g; s/`[^`]*`//g; s/\*\*([^*]*)\*\*/\1/g; s/\*([^*]*)\*/\1/g; s/^#+\s*//gm; s/\[([^]]*)\]\([^)]*\)/\1/g')

# Ensure newlines become sentence breaks so TTS pauses naturally
MSG=$(echo "$MSG" | sed -E '/^$/d' | sed -E 's/([^.!?])$/\1./' | tr '\n' ' ')

# Space out ticket IDs (e.g. BEA-543 → B E A 5 4 3) so TTS reads them clearly
MSG=$(echo "$MSG" | sed -E 's/\b([A-Z]{1,3})-([0-9]{1,5})\b/\1 \2/g' | sed -E 's/\b([A-Z])([A-Z])([A-Z])\b/\1 \2 \3/g; s/\b([A-Z])([A-Z])\b/\1 \2/g' | sed -E 's/([A-Z]) ([0-9])([0-9])([0-9])([0-9])([0-9])\b/\1 \2 \3 \4 \5 \6/g; s/([A-Z]) ([0-9])([0-9])([0-9])([0-9])\b/\1 \2 \3 \4 \5/g; s/([A-Z]) ([0-9])([0-9])([0-9])\b/\1 \2 \3 \4/g; s/([A-Z]) ([0-9])([0-9])\b/\1 \2 \3/g')

~/projects/llama-voice-hotkeys/.venv/bin/llama-voice "$MSG" &
