#!/bin/zsh
set -eu

REPO_DIR="${REPO_DIR:-/Users/bruce/Coding/NewsRadar}"
PROJECT_DIR="$REPO_DIR/TrendRadar"
SITE_DIR="$REPO_DIR/docs"
DOMAIN="${NEWSRADAR_SITE_DOMAIN:-newsradar.ccwu.cc}"
GIT_PUSH="${NEWSRADAR_SITE_GIT_PUSH:-1}"

INDEX_FILE="$PROJECT_DIR/output/index.html"
HTML_DIR="$PROJECT_DIR/output/html"

if [ ! -f "$INDEX_FILE" ]; then
  echo "[site] missing report index: $INDEX_FILE"
  exit 0
fi

mkdir -p "$SITE_DIR/reports"

cp "$INDEX_FILE" "$SITE_DIR/index.html"
rsync -a --exclude='*/notification_test_*.html' "$HTML_DIR/" "$SITE_DIR/reports/"
printf "%s\n" "$DOMAIN" > "$SITE_DIR/CNAME"
touch "$SITE_DIR/.nojekyll"
python3 "$REPO_DIR/scripts/generate_reports_archive.py"

echo "[site] reports synced to $SITE_DIR"
echo "[site] custom domain: $DOMAIN"

if [ "$GIT_PUSH" != "1" ]; then
  exit 0
fi

cd "$REPO_DIR"

git add docs/CNAME docs/.nojekyll docs/archive.html docs/index.html docs/reports TrendRadar/index.html

if git diff --cached --quiet; then
  echo "[site] no report changes to publish"
  exit 0
fi

git commit -m "docs: publish latest TrendRadar report"
git push origin main
