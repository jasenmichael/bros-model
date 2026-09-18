#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLAMA_CPP="${1:-}"

if [[ -z "${LLAMA_CPP}" ]]; then
  echo "usage: bash scripts/convert-to-gguf.sh /path/to/llama.cpp" >&2
  exit 1
fi

if [[ ! -d "${LLAMA_CPP}" ]]; then
  echo "llama.cpp path is not a directory: ${LLAMA_CPP}" >&2
  exit 1
fi

MERGED="${ROOT}/output/merged"
if [[ ! -f "${MERGED}/config.json" ]]; then
  echo "merged Hugging Face model not found at ${MERGED}" >&2
  echo "run: python scripts/merge-adapter.py" >&2
  exit 1
fi

CONVERT=""
for candidate in \
  "${LLAMA_CPP}/convert_hf_to_gguf.py" \
  "${LLAMA_CPP}/convert-hf-to-gguf.py"; do
  if [[ -f "${candidate}" ]]; then
    CONVERT="${candidate}"
    break
  fi
done
if [[ -z "${CONVERT}" ]]; then
  echo "could not find convert_hf_to_gguf.py under ${LLAMA_CPP}" >&2
  exit 1
fi

QUANTIZE=""
for candidate in \
  "${LLAMA_CPP}/llama-quantize" \
  "${LLAMA_CPP}/build/bin/llama-quantize" \
  "${LLAMA_CPP}/bin/llama-quantize"; do
  if [[ -x "${candidate}" ]]; then
    QUANTIZE="${candidate}"
    break
  fi
done
if [[ -z "${QUANTIZE}" ]]; then
  echo "could not find llama-quantize under ${LLAMA_CPP}" >&2
  exit 1
fi

GGUF_DIR="${ROOT}/output/gguf"
MODELS_DIR="${ROOT}/models"
mkdir -p "${GGUF_DIR}" "${MODELS_DIR}"

F16_OUT="${GGUF_DIR}/bros-f16.gguf"
PYTHON="${PYTHON:-}"
if [[ -z "${PYTHON}" && -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON="${ROOT}/.venv/bin/python"
fi
if [[ -z "${PYTHON}" ]]; then
  PYTHON="python3"
fi

echo "converting ${MERGED} -> ${F16_OUT}"
"${PYTHON}" "${CONVERT}" "${MERGED}" --outtype f16 --outfile "${F16_OUT}"

MAX_BYTES=$((100 * 1024 * 1024))
PACKAGED="${MODELS_DIR}/bros-q4_k_m.gguf"
SELECTED_TYPE=""

try_quant() {
  local qtype="$1"
  local dest="$2"
  echo "quantizing ${F16_OUT} -> ${dest} (${qtype})"
  "${QUANTIZE}" "${F16_OUT}" "${dest}" "${qtype}"
}

try_quant "Q4_K_M" "${PACKAGED}"
SELECTED_TYPE="Q4_K_M"
SIZE="$(stat -c%s "${PACKAGED}")"
if (( SIZE > MAX_BYTES )); then
  echo "Q4_K_M is ${SIZE} bytes (> 100 MB); trying Q4_0"
  try_quant "Q4_0" "${PACKAGED}"
  SELECTED_TYPE="Q4_0"
  SIZE="$(stat -c%s "${PACKAGED}")"
fi
if (( SIZE > MAX_BYTES )); then
  echo "Q4_0 is ${SIZE} bytes (> 100 MB); trying Q3_K_M"
  try_quant "Q3_K_M" "${PACKAGED}"
  SELECTED_TYPE="Q3_K_M"
  SIZE="$(stat -c%s "${PACKAGED}")"
fi

echo "packaged ${PACKAGED} (${SELECTED_TYPE}, ${SIZE} bytes)"
if (( SIZE > MAX_BYTES )); then
  echo "warning: packaged GGUF is still over 100 MB (${SIZE} bytes)" >&2
fi
