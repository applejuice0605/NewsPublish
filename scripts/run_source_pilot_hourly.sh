#!/bin/zsh
set -eu

SCRIPT_DIR="${0:A:h}"
REPO_DIR="${REPO_DIR:-${SCRIPT_DIR:h}}"
PROJECT_DIR="$REPO_DIR/TrendRadar"
LOCK_DIR="/tmp/newsradar-source-pilot.lock"
ENV_FILE="$PROJECT_DIR/.env.local"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] previous source pilot run still active, skipping"
  exit 0
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

cd "$REPO_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting isolated source pilot"
python3 "$REPO_DIR/scripts/run_source_pilot.py" >/dev/null
echo "[$(date '+%Y-%m-%d %H:%M:%S')] finished isolated source pilot"
