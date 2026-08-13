#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RAW_LABEL=${1:-pre-update}
LABEL=$(printf '%s' "$RAW_LABEL" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+|-+$//g')
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_ROOT=${BIDBOARD_BACKUP_ROOT:-"$(dirname "$REPO_ROOT")/Backups/BidBoard"}

if [[ -z "$LABEL" ]]; then
  echo "Backup label must contain at least one letter or number." >&2
  exit 2
fi

cd "$REPO_ROOT"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to back up a dirty worktree. Commit or stash changes first." >&2
  exit 1
fi

HEAD_COMMIT=$(git rev-parse HEAD)
TAG="backup/${LABEL}-${STAMP}"
BUNDLE="$BACKUP_ROOT/bidboard-${LABEL}-${STAMP}.bundle"
SNAPSHOT="$BACKUP_ROOT/${LABEL}-${STAMP}"

mkdir -p "$BACKUP_ROOT"
git tag -a "$TAG" "$HEAD_COMMIT" -m "BidBoard backup before ${LABEL} ${STAMP}"
git bundle create "$BUNDLE" --branches --tags
git bundle verify "$BUNDLE" >/dev/null
git clone --quiet "$BUNDLE" "$SNAPSHOT"
git -C "$SNAPSHOT" checkout --quiet "$HEAD_COMMIT"

if git remote get-url origin >/dev/null 2>&1; then
  git push origin "$TAG"
fi

cat <<EOF
Backup complete
  tag:      $TAG
  commit:   $HEAD_COMMIT
  bundle:   $BUNDLE
  snapshot: $SNAPSHOT
EOF
