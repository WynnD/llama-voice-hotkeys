#!/usr/bin/env bash
# Warm up the TTS model on llama-swap so first speech is instant
curl -s -o /dev/null -X POST http://192.168.0.101:8080/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro-82m","voice":"af_sky","input":".","response_format":"wav","speed":1.0}' &
