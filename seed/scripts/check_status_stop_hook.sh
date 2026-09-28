#!/usr/bin/env bash
# Stop hook: before Claude ends a turn, run scripts/check_status.sh if anything
# under journal/ has changed, and refuse to stop while it fails. See
# journal/misc/status_and_terraparse_rfcs.md and docs/conventions.md's
# "TerraParse RFCs and STATUS.md" section.
#
# Runs only when journal/ has uncommitted changes, so a session that touched no
# journal doc is never blocked by a failure it did not cause. It lets the turn
# end when `stop_hook_active` is true, so a check that cannot be fixed cannot
# trap the session in a loop. Synchronous on purpose: it must read stdin.
#
# Same family as scripts/check_claude_md_hook.sh (a PreToolUse hook on the
# content about to be written). This one runs after the work, on the files.
set -euo pipefail

input="$(cat)"

if [ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false')" = "true" ]; then
    exit 0
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

[ -n "$(git status --porcelain -- journal)" ] || exit 0

if out="$(scripts/check_status.sh 2>&1)"; then
    exit 0
fi

reason="scripts/check_status.sh fails, and journal/ has uncommitted changes. Fix the failures below, then stop. If STATUS.md is stale, run: venv/bin/python scripts/build_status.py

$(printf '%s\n' "$out" | tail -n 30)"

jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
