#!/usr/bin/env bash
# Open or update one Bros pull request for a bros-model release tag.
#
#   scripts/open-bros-pr.sh vX.Y.Z
#
# Uses BROS_REPO_TOKEN (contents and pull-requests write on jasenmichael/bros).
# Does not use GITHUB_TOKEN for that repo. Does not push to Bros main.
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'usage: scripts/open-bros-pr.sh vX.Y.Z\n' >&2
  exit 1
fi

tag="$1"
model_version="${tag#v}"

if [[ -z "${BROS_REPO_TOKEN:-}" ]]; then
  printf 'BROS_REPO_TOKEN is unset\n' >&2
  exit 1
fi

unset GITHUB_TOKEN || true
export GH_TOKEN="$BROS_REPO_TOKEN"
export GIT_TERMINAL_PROMPT=0

askpass="$(mktemp)"
workdir="$(mktemp -d)"
cleanup() {
  rm -rf "$workdir"
  rm -f "$askpass"
}
trap cleanup EXIT

cat >"$askpass" <<'EOF'
#!/bin/sh
case "$1" in
  *Username*) printf '%s\n' "x-access-token" ;;
  *) printf '%s\n' "$BROS_REPO_TOKEN" ;;
esac
EOF
chmod 700 "$askpass"
export GIT_ASKPASS="$askpass"

pin_submodule() {
  local model_tag="$1"
  local url="https://github.com/jasenmichael/bros-model.git"
  local current=""
  if [[ -f .gitmodules ]]; then
    current="$(git config -f .gitmodules --get submodule.vendor/bros-model.url || true)"
  fi
  if [[ -z "$current" ]]; then
    git submodule add "$url" vendor/bros-model
  else
    if [[ "$current" != "$url" ]]; then
      git config -f .gitmodules submodule.vendor/bros-model.url "$url"
    fi
    git submodule sync -- vendor/bros-model
    git submodule update --init -- vendor/bros-model
  fi
  git -C vendor/bros-model fetch --tags origin
  git -C vendor/bros-model checkout --detach "refs/tags/${model_tag}"
  git add -- .gitmodules vendor/bros-model
}

git clone https://github.com/jasenmichael/bros.git "$workdir/bros"
cd "$workdir/bros"
git fetch origin main

pr_line="$(gh pr list --repo jasenmichael/bros --state open --limit 100 --json number,headRefName --jq '
  [.[] | select(.headRefName | startswith("bros-model-v"))]
  | if length == 0 then "" else "\(.[0].number)\t\(.[0].headRefName)" end
')"

updating=0
if [[ -n "$pr_line" ]]; then
  updating=1
  pr_number="${pr_line%%$'\t'*}"
  branch="${pr_line#*$'\t'}"
  git checkout -B "$branch" origin/main
else
  branch="bros-model-v${model_version}"
  git checkout -b "$branch" origin/main
fi

printf '%s\n' "$model_version" > lib/apps/core/ollama/BROS_MODEL_VERSION
pin_submodule "$tag"
git add -- lib/apps/core/ollama/BROS_MODEL_VERSION
scripts/bump.sh minor
new_version="$(tr -d '[:space:]' < VERSION)"
title="$(git log -1 --format=%s)"

if git ls-remote --exit-code --heads origin "refs/heads/${branch}" >/dev/null 2>&1; then
  git fetch origin "+refs/heads/${branch}:refs/remotes/origin/${branch}"
  git push --force-with-lease="refs/heads/${branch}:refs/remotes/origin/${branch}" origin "HEAD:${branch}"
else
  git push -u origin "HEAD:${branch}"
fi

body="$(printf '%s\n%s\n%s\n' \
  "$tag" \
  "$new_version" \
  "Merging publishes the Bros tarballs from this commit and must not bump VERSION again.")"

if [[ "$updating" -eq 1 ]]; then
  gh pr edit "$pr_number" --repo jasenmichael/bros --title "$title" --body "$body"
else
  gh pr create --repo jasenmichael/bros --base main --head "$branch" --title "$title" --body "$body"
fi
