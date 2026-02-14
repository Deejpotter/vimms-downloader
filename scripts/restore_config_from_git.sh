#!/usr/bin/env bash
# Restore vimms_config.json from the most recent commit that contains it
# Usage: ./scripts/restore_config_from_git.sh [<commit-ish>] [--yes]

set -euo pipefail
repo_root=$(cd "$(dirname "$0")/.." && pwd -P)
cd "$repo_root"

commit="$1"
force=false
if [ "${commit:-}" = "--yes" ]; then
  commit=""
  force=true
fi
if [ "${2:-}" = "--yes" ]; then
  force=true
fi

if [ -z "$commit" ]; then
  commit=$(git rev-list -n 1 HEAD -- vimms_config.json || true)
  if [ -z "$commit" ]; then
    echo "No commit in history contains vimms_config.json"
    exit 1
  fi
fi

echo "Restore vimms_config.json from commit: $commit"
if [ "$force" = false ]; then
  read -p "This will overwrite the working copy of vimms_config.json. Continue? (y/N) " yn
  case "$yn" in
    [Yy]*) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

git show "$commit":vimms_config.json > vimms_config.json
echo "Restored vimms_config.json from $commit"

echo "Creating backup of current working copy at vimms_config.json.bak"
cp -f vimms_config.json vimms_config.json.bak || true

echo "Done."