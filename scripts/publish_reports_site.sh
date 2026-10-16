#!/bin/zsh
set -eu

REPO_DIR="${REPO_DIR:-/Users/bruce/Coding/NewsRadar}"
PROJECT_DIR="$REPO_DIR/TrendRadar"
SITE_DIR="$REPO_DIR/docs"
DOMAIN="${NEWSRADAR_SITE_DOMAIN:-newsradar.ccwu.cc}"
GIT_PUSH="${NEWSRADAR_SITE_GIT_PUSH:-1}"

INDEX_FILE="$PROJECT_DIR/output/index.html"
HTML_DIR="$PROJECT_DIR/output/html"
AUDIO_DIR="$PROJECT_DIR/output/audio"

if [ ! -f "$INDEX_FILE" ]; then
  echo "[site] missing report index: $INDEX_FILE"
  exit 0
fi

mkdir -p "$SITE_DIR/reports"

cp "$INDEX_FILE" "$SITE_DIR/index.html"
rsync -a --exclude='*/notification_test_*.html' "$HTML_DIR/" "$SITE_DIR/reports/"
if [ -d "$AUDIO_DIR" ]; then
  mkdir -p "$SITE_DIR/audio"
  rsync -a "$AUDIO_DIR/" "$SITE_DIR/audio/"
fi
printf "%s\n" "$DOMAIN" > "$SITE_DIR/CNAME"
touch "$SITE_DIR/.nojekyll"
python3 "$REPO_DIR/scripts/generate_reports_archive.py"
if [ -f "$REPO_DIR/scripts/generate_site_insights.py" ]; then
  python3 "$REPO_DIR/scripts/generate_site_insights.py"
fi

echo "[site] reports synced to $SITE_DIR"
echo "[site] custom domain: $DOMAIN"

if [ "$GIT_PUSH" != "1" ]; then
  exit 0
fi

cd "$REPO_DIR"

git add docs/CNAME docs/.nojekyll docs/archive.html docs/index.html docs/assets \
  docs/reports TrendRadar/index.html
if [ -d docs/audio ]; then
  git add docs/audio
fi
for insight_file in docs/health.json docs/status.html docs/trends.html docs/trends.json; do
  if [ -e "$insight_file" ]; then
    git add "$insight_file"
  fi
done

if git diff --cached --quiet; then
  echo "[site] no report changes to publish"
  exit 0
fi

git commit -m "docs: publish latest TrendRadar report"
git push origin main
