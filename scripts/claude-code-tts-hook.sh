#!/usr/bin/env bash
# Claude Code Stop hook: speak the assistant's last message via TTS
set -euo pipefail

INPUT=$(cat)

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

~/projects/llama-voice-hotkeys/.venv/bin/llama-voice "$MSG" &
