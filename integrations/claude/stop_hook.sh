#!/usr/bin/env bash
# Stop hook: before Claude ends a turn, run `terrastep check --if-changed`
# and refuse to stop while it fails. See journal/origin/handoff.md.
#
# `--if-changed` is silent and exits 0 when scan_dirs has no uncommitted
# change, so a session that touched nothing terrastep tracks is never
# blocked by a failure it did not cause. It lets the turn end when
# `stop_hook_active` is true, so a check that cannot be fixed cannot trap
# the session in a loop. Synchronous on purpose: it must read stdin.
set -euo pipefail

input="$(cat)"

if [ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false')" = "true" ]; then
    exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

terrastep_bin="$repo_root/venv/bin/terrastep"
[ -x "$terrastep_bin" ] || terrastep_bin="terrastep"

if out="$("$terrastep_bin" check --if-changed 2>&1)"; then
    exit 0
fi

reason="terrastep check fails, and its scan_dirs have uncommitted changes. Fix the failures below, then stop. If the index is stale, run: terrastep build

$(printf '%s\n' "$out" | tail -n 30)"

jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
