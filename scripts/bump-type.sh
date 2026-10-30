#!/usr/bin/env bash
# Print patch, minor, major, or nothing from conventional commits.
#
#   scripts/bump-type.sh <base-ref>
#   scripts/bump-type.sh --self-check
set -euo pipefail

rank_name() {
  case "$1" in
    major) printf '3\n' ;;
    minor) printf '2\n' ;;
    patch) printf '1\n' ;;
    *) printf '0\n' ;;
  esac
}

name_of() {
  case "$1" in
    3) printf 'major\n' ;;
    2) printf 'minor\n' ;;
    1) printf 'patch\n' ;;
  esac
}

type_of() {
  local subject="$1" body="$2" kind
  if [[ "$subject" == chore:\ bump\ * ]]; then
    return 0
  fi
  if [[ "$body" == *"BREAKING CHANGE"* || "$subject" == feat!:* || "$subject" == feat'('*')!:'* ]]; then
    printf 'major\n'
    return 0
  fi
  kind="${subject%%:*}"
  kind="${kind%%(*}"
  case "$kind" in
    feat) printf 'minor\n' ;;
    fix|perf) printf 'patch\n' ;;
  esac
}

best_of_log() {
  local base="$1" best=0 record subject body kind r
  while IFS= read -r -d $'\x1e' record || [[ -n "$record" ]]; do
    [[ -z "$record" ]] && continue
    subject="${record%%$'\0'*}"
    if [[ "$record" == *$'\0'* ]]; then
      body="${record#*$'\0'}"
    else
      body=""
    fi
    kind="$(type_of "$subject" "$body")"
    r="$(rank_name "$kind")"
    if [[ "$r" -gt "$best" ]]; then
      best="$r"
    fi
  done < <(git log --format='%s%x00%b%x1e' "${base}..HEAD")
  name_of "$best"
}

case "${1:-}" in
  --self-check)
    [[ "$(type_of 'feat: add' '')" == "minor" ]]
    [[ "$(type_of 'fix: bug' '')" == "patch" ]]
    [[ "$(type_of 'perf: fast' '')" == "patch" ]]
    [[ "$(type_of 'feat!: break' '')" == "major" ]]
    [[ "$(type_of 'feat: x' $'note\nBREAKING CHANGE: y')" == "major" ]]
    [[ -z "$(type_of 'docs: note' '')" ]]
    [[ -z "$(type_of 'chore: tidy' '')" ]]
    [[ -z "$(type_of 'refactor: tidy' '')" ]]
    [[ -z "$(type_of 'test: cover' '')" ]]
    [[ -z "$(type_of 'ci: flow' '')" ]]
    [[ -z "$(type_of 'chore: bump minor to 1.1.0' '')" ]]
    printf 'self-check ok\n' >&2
    ;;
  "")
    printf 'usage: scripts/bump-type.sh <base-ref>\n' >&2
    exit 2
    ;;
  *)
    best_of_log "$1"
    ;;
esac
