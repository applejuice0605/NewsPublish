#!/bin/zsh
set -eu

REPO_DIR="${REPO_DIR:-/Users/bruce/Coding/NewsRadar}"
APPROVAL="${1:-}"

if [ "$APPROVAL" != "--approved" ]; then
  echo "usage: $0 --approved"
  echo "This command publishes the current staging commit to production."
  exit 2
fi

cd "$REPO_DIR"
BRANCH="$(git branch --show-current)"
if [ "$BRANCH" != "staging" ]; then
  echo "[production] promotion must run from the staging branch (current: $BRANCH)"
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "[production] working tree is not clean"
  exit 1
fi

git fetch origin main staging
if ! git merge-base --is-ancestor origin/main HEAD; then
  echo "[production] staging does not contain the latest production commits"
  echo "[production] merge origin/main into staging, resolve/test, then retry"
  exit 1
fi

python3 tests/test_preview_site.py
zsh -n scripts/*.sh

COMMIT="$(git rev-parse HEAD)"
echo "[production] promoting $COMMIT"
git push origin HEAD:main
echo "[production] pushed to main; Cloudflare production build will deploy newsradar.ccwu.cc"
