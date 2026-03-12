#!/usr/bin/env bash
# Sets up:
#   1. GNOME hotkey (Ctrl+Shift+R) to read highlighted text aloud
#   2. Claude Code Stop hook to speak assistant responses
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOTKEY="${1:-<Primary><Shift>r}"

# --- Prerequisites ---

if ! command -v gsettings >/dev/null 2>&1; then
  echo "gsettings is required (GNOME session)." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required." >&2
  exit 1
fi

if ! command -v wl-paste >/dev/null 2>&1; then
  echo "wl-clipboard is required (wl-paste)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

# --- 1. GNOME read-selection hotkey ---

SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
CUSTOM_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/llama-voice-read-selection/"

CURRENT="$(gsettings get "$SCHEMA" custom-keybindings)"
# ast.literal_eval is safe — it only parses Python literals, no code execution
UPDATED="$(printf '%s' "$CURRENT" | python3 - "$CUSTOM_PATH" <<'PY'
import ast, sys
raw = sys.stdin.read().strip()
path = sys.argv[1]
try:
    items = ast.literal_eval(raw)
except Exception:
    items = []
if not isinstance(items, list):
    items = []
if path not in items:
    items.append(path)
print(items)
PY
)"

gsettings set "$SCHEMA" custom-keybindings "$UPDATED"
gsettings set "$CUSTOM_SCHEMA:$CUSTOM_PATH" name "Read Selection Aloud"
gsettings set "$CUSTOM_SCHEMA:$CUSTOM_PATH" command "$SCRIPT_DIR/read-selection.sh"
gsettings set "$CUSTOM_SCHEMA:$CUSTOM_PATH" binding "$HOTKEY"

echo "GNOME shortcut configured:"
echo "  binding: $HOTKEY"
echo "  command: $SCRIPT_DIR/read-selection.sh"

# --- 2. Claude Code Stop hook ---

CLAUDE_SETTINGS="$HOME/.claude/settings.json"

if [ ! -f "$CLAUDE_SETTINGS" ]; then
  echo "{}" > "$CLAUDE_SETTINGS"
fi

HOOK_CMD="$SCRIPT_DIR/claude-code-tts-hook.sh"

# Check if hook is already configured
if jq -e ".hooks.Stop[]?.hooks[]? | select(.command == \"$HOOK_CMD\")" "$CLAUDE_SETTINGS" >/dev/null 2>&1; then
  echo "Claude Code TTS hook already configured."
else
  # Add the Stop hook using jq
  UPDATED_SETTINGS=$(jq \
    --arg cmd "$HOOK_CMD" \
    '.hooks.Stop = ((.hooks.Stop // []) + [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": $cmd,
        "timeout": 120,
        "async": true
      }]
    }])' "$CLAUDE_SETTINGS")
  echo "$UPDATED_SETTINGS" > "$CLAUDE_SETTINGS"
  echo "Claude Code TTS hook added to $CLAUDE_SETTINGS"
fi

echo ""
echo "Done! Highlight text and press $HOTKEY to read it aloud."
echo "Claude Code will speak responses automatically."
