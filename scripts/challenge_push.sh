#!/usr/bin/env bash
# Commit trading/ and push to the challenge branch. Survives overlapping runs:
# journal files are per run, and a state.json conflict is merged by challenge.py.
set -u
cd "$(dirname "$0")/.."
BRANCH=claude/mcp-trading-server-f75a0v
MSG=${1:-"Challenge run $(TZ=America/New_York date '+%Y-%m-%d %H:%M') ET"}
git add trading
git diff --cached --quiet || git commit -qm "$MSG"
for delay in 2 4 8 16; do
  git push -q -u origin "HEAD:$BRANCH" && { echo pushed; exit 0; }
  git fetch -q origin "$BRANCH" || { sleep "$delay"; continue; }
  mine=$(mktemp); theirs=$(mktemp)
  git show HEAD:trading/state.json > "$mine"
  if ! git rebase -q "origin/$BRANCH"; then
    git show "origin/$BRANCH:trading/state.json" > "$theirs"
    python3 scripts/challenge.py merge-state "$mine" "$theirs" > trading/state.json
    git add trading/state.json
    GIT_EDITOR=true git rebase --continue || { git rebase --abort; echo "rebase failed"; exit 1; }
  fi
  sleep "$delay"
done
echo "push failed after 4 tries"
exit 1
