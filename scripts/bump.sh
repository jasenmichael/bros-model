#!/usr/bin/env bash
# Write VERSION and commit it on the current branch. Does not push.
# Leaves pyproject.toml alone.
#
#   scripts/bump.sh patch|minor|major
#   scripts/bump.sh --self-check
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

next_version() {
  python3 - "$1" "$2" <<'PY'
import sys
cur, kind = sys.argv[1], sys.argv[2]
parts = cur.split(".")
if len(parts) != 3 or any(not p.isdigit() for p in parts):
    raise SystemExit(f"VERSION is not X.Y.Z: {cur}")
major, minor, patch = (int(p) for p in parts)
if kind == "major":
    major, minor, patch = major + 1, 0, 0
elif kind == "minor":
    minor, patch = minor + 1, 0
elif kind == "patch":
    patch += 1
else:
    raise SystemExit(f"unknown bump: {kind}")
print(f"{major}.{minor}.{patch}")
PY
}

commit_bump() {
  local msg="$1"
  git add VERSION
  if git diff --cached --quiet; then
    printf 'nothing to commit\n' >&2
    exit 1
  fi
  if git config user.name >/dev/null 2>&1 && git config user.email >/dev/null 2>&1; then
    git commit -m "$msg"
  else
    git -c user.name="$(git log -1 --format='%an')" -c user.email="$(git log -1 --format='%ae')" commit -m "$msg"
  fi
}

case "${1:-}" in
  --self-check)
    [[ "$(next_version 1.0.0 patch)" == "1.0.1" ]]
    [[ "$(next_version 1.0.0 minor)" == "1.1.0" ]]
    [[ "$(next_version 1.0.0 major)" == "2.0.0" ]]
    printf 'self-check ok\n' >&2
    ;;
  patch|minor|major)
    cur="$(tr -d '[:space:]' < VERSION)"
    next="$(next_version "$cur" "$1")"
    printf '%s\n' "$next" > VERSION
    commit_bump "chore: bump $1 to $next"
    printf '%s\n' "$next"
    ;;
  *)
    printf 'usage: scripts/bump.sh patch|minor|major\n' >&2
    exit 2
    ;;
esac
