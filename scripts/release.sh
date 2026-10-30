#!/usr/bin/env bash
# Pack models/, ollama/, and scripts/. Read VERSION. Do not bump it.
#
#   scripts/release.sh              # pack and print the tag
#   scripts/release.sh --self-check # assertions only; no tar
#   scripts/release.sh --paths      # stdin: newline-separated paths
#                                   # exit 0 if a packaged path changed, else 1
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# True when any path is under models/, ollama/, or scripts/.
packaged_paths_changed() {
  local path changed=0
  while IFS= read -r path || [[ -n "${path}" ]]; do
    path="${path%$'\r'}"
    path="${path#./}"
    [[ -z "$path" ]] && continue
    case "$path" in
      models | models/* | ollama | ollama/* | scripts | scripts/*)
        changed=1
        ;;
    esac
  done
  [[ "$changed" -eq 1 ]]
}

self_check() {
  local sample

  if printf 'README.md\n' | packaged_paths_changed; then
    printf 'README.md counted as packaged\n' >&2
    exit 1
  fi
  if printf 'README.md\nPLAN.md\n' | packaged_paths_changed; then
    printf 'unpackaged path list counted as packaged\n' >&2
    exit 1
  fi

  for sample in models/bros-q4_k_m.gguf ollama/Modelfile scripts/install-ollama.sh; do
    if ! printf '%s\n' "$sample" | packaged_paths_changed; then
      printf 'packaged path missed: %s\n' "$sample" >&2
      exit 1
    fi
  done
  if ! printf 'README.md\nmodels/bros-q4_k_m.gguf\n' | packaged_paths_changed; then
    printf 'mixed path list missed the packaged path\n' >&2
    exit 1
  fi

  printf 'self-check ok\n' >&2
}

release() {
  local version tag
  version="$(tr -d '[:space:]' < VERSION)"
  if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'VERSION is not X.Y.Z: %s\n' "$version" >&2
    exit 1
  fi
  tag="v${version}"
  GIT_TERMINAL_PROMPT=0 git fetch --tags --force origin >&2 || true
  if git show-ref --verify --quiet "refs/tags/${tag}" || git ls-remote --tags origin "refs/tags/${tag}" | grep -q .; then
    printf '%s already exists. Bump VERSION in a pull request.\n' "$tag" >&2
    exit 1
  fi
  tar -czf bros-model.tar.gz models ollama scripts
  printf '%s\n' "$tag"
}

case "${1:-}" in
  --self-check)
    self_check
    ;;
  --paths)
    if packaged_paths_changed; then
      exit 0
    fi
    exit 1
    ;;
  "")
    release
    ;;
  *)
    printf 'usage: scripts/release.sh [--self-check|--paths]\n' >&2
    exit 2
    ;;
esac
