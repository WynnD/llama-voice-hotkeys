#!/usr/bin/env bash
# Stop all TTS audio playback immediately
pkill -f 'ffplay.*-nodisp.*-autoexit' 2>/dev/null || true
