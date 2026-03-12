#!/usr/bin/env bash
# Sets up:
#   1. GNOME hotkey (Ctrl+Shift+R) to read highlighted text aloud
#   2. GNOME hotkey (Ctrl+Shift+Q) to stop TTS playback
#   3. Claude Code Stop hook to speak assistant responses
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
READ_HOTKEY="${1:-<Primary><Shift>r}"
STOP_HOTKEY="${2:-<Primary><Shift>q}"

# --- Prerequisites ---

for cmd in gsettings jq wl-paste python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required." >&2
    exit 1
  fi
done

# --- Helper: register a GNOME custom shortcut idempotently ---

SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"

add_gnome_shortcut() {
  local slug="$1" name="$2" command="$3" binding="$4"
  local custom_path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/${slug}/"

  # ast.literal_eval is safe — it only parses Python literals, no code execution
  local current updated
  current="$(gsettings get "$SCHEMA" custom-keybindings)"
  updated="$(echo "$current" | python3 -c "
import ast, sys
raw = sys.stdin.read().strip()
path = '$custom_path'
try:
    items = ast.literal_eval(raw)
except Exception:
    items = []
if not isinstance(items, list):
    items = []
if path not in items:
    items.append(path)
print(items)
")"

  gsettings set "$SCHEMA" custom-keybindings "$updated"
  gsettings set "$CUSTOM_SCHEMA:$custom_path" name "$name"
  gsettings set "$CUSTOM_SCHEMA:$custom_path" command "$command"
  gsettings set "$CUSTOM_SCHEMA:$custom_path" binding "$binding"

  echo "GNOME shortcut: $name ($binding)"
}

# --- 1. Read-selection hotkey ---

add_gnome_shortcut "llama-voice-read-selection" "Read Selection Aloud" \
  "$SCRIPT_DIR/read-selection.sh" "$READ_HOTKEY"

# --- 2. Stop TTS hotkey ---

add_gnome_shortcut "llama-voice-stop-tts" "Stop TTS" \
  "$SCRIPT_DIR/stop-tts.sh" "$STOP_HOTKEY"

# --- 3. Claude Code Stop hook ---

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
echo "Done!"
echo "  Ctrl+Shift+R  Read highlighted text aloud"
echo "  Ctrl+Shift+Q  Stop TTS playback"
echo "  Claude Code   Speaks responses automatically"
