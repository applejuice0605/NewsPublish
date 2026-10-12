#!/bin/zsh
set -eu

PROJECT_DIR="/Users/bruce/Coding/NewsRadar/TrendRadar"
UV_BIN="/opt/homebrew/bin/uv"
LOG_DIR="$PROJECT_DIR/output/logs"
LOCK_DIR="/tmp/newsradar-trendradar.lock"

mkdir -p "$LOG_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] previous TrendRadar run still active, skipping"
  exit 0
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$PROJECT_DIR"
export PYTHONUNBUFFERED=1
export TRENDRADAR_NO_BROWSER=1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting TrendRadar hourly run"
"$UV_BIN" run python -m trendradar
echo "[$(date '+%Y-%m-%d %H:%M:%S')] finished TrendRadar hourly run"
