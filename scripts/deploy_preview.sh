#!/bin/zsh
set -eu

REPO_DIR="${REPO_DIR:-/Users/bruce/Coding/NewsRadar}"
PREVIEW_DIR="$REPO_DIR/.deploy/preview"

cd "$REPO_DIR"
BRANCH="$(git branch --show-current)"
if [ "$BRANCH" != "staging" ] && [ "${NEWSRADAR_ALLOW_NON_STAGING_PREVIEW:-0}" != "1" ]; then
  echo "[preview] expected branch 'staging', found '$BRANCH'"
  echo "[preview] set NEWSRADAR_ALLOW_NON_STAGING_PREVIEW=1 only for an intentional one-off preview"
  exit 1
fi

NEWSRADAR_SITE_APPLY_FEATURES=0 NEWSRADAR_SITE_GIT_PUSH=0 "$REPO_DIR/scripts/publish_reports_site.sh"
python3 "$REPO_DIR/scripts/prepare_preview_site.py" \
  --repo "$REPO_DIR" \
  --source "$REPO_DIR/docs" \
  --destination "$PREVIEW_DIR"
python3 "$REPO_DIR/scripts/apply_site_features.py" \
  --site-dir "$PREVIEW_DIR" \
  --environment preview \
  --speech "${NEWSRADAR_FEATURE_SPEECH:-}" \
  --trends "${NEWSRADAR_FEATURE_TRENDS:-}" \
  --status "${NEWSRADAR_FEATURE_STATUS:-}" \
  --sources "${NEWSRADAR_FEATURE_SOURCES:-}"

echo "[preview] deploying newsradar-preview"
npx wrangler deploy --env preview
echo "[preview] deployed: https://preview.newsradar.ccwu.cc"
