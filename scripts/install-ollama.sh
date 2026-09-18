#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_NAME="${OLLAMA_MODEL_NAME:-bros}"
GGUF="${ROOT}/models/bros-q4_k_m.gguf"
MODELFILE="${ROOT}/ollama/Modelfile"

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not found on PATH" >&2
  exit 1
fi

if [[ ! -f "${GGUF}" ]]; then
  echo "missing packaged model: ${GGUF}" >&2
  echo "train, merge, and convert first, or clone a repo that already contains models/bros-q4_k_m.gguf" >&2
  exit 1
fi

if [[ ! -f "${MODELFILE}" ]]; then
  echo "missing ${MODELFILE}" >&2
  exit 1
fi

ollama create "${MODEL_NAME}" -f "${MODELFILE}"
echo "created Ollama model ${MODEL_NAME}"
