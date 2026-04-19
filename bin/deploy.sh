#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/srv/stacks/ops-hub"
LOCK_DIR="/tmp/ops-hub-deploy.lock"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Deploy already running. Exiting."
  exit 0
fi
trap 'rmdir "$LOCK_DIR"' EXIT

cd "$REPO_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting ops-hub deploy..."
if /usr/bin/git remote get-url origin >/dev/null 2>&1; then
  /usr/bin/git pull --ff-only
else
  echo "No git origin configured. Skipping git pull."
fi
/usr/bin/docker compose up -d --build
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ops-hub deploy complete."
