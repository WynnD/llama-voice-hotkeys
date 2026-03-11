#!/usr/bin/env bash
set -euo pipefail

HOTKEY="${1:-'<Primary><Alt>space>'}"
COMMAND="${2:-llama-voice toggle}"
NAME="llama-voice toggle"

if ! command -v gsettings >/dev/null 2>&1; then
  echo "gsettings is required (GNOME session)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
CUSTOM_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/llama-voice-toggle/"

CURRENT="$(gsettings get "$SCHEMA" custom-keybindings)"
UPDATED="$(printf '%s' "$CURRENT" | python3 - "$CUSTOM_PATH" <<'PY'
import ast
import sys

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
gsettings set "$CUSTOM_SCHEMA:$CUSTOM_PATH" name "$NAME"
gsettings set "$CUSTOM_SCHEMA:$CUSTOM_PATH" command "$COMMAND"
gsettings set "$CUSTOM_SCHEMA:$CUSTOM_PATH" binding "$HOTKEY"

echo "Configured GNOME shortcut:"
echo "  name: $NAME"
echo "  command: $COMMAND"
echo "  binding: $HOTKEY"
