#!/usr/bin/env bash
# PreToolUse hook (Edit|Write): blocks a write that introduces a dated
# "## ... (YYYY-MM-DD)" section heading into CLAUDE.md or
# docs/conventions.md. See scripts/check_claude_md.sh and
# docs/conventions.md's "Maintaining CLAUDE.md" entry — this is the
# same check, applied to the content about to be written rather than
# to the file already on disk, since a PreToolUse hook fires before
# the edit lands.
set -euo pipefail

input="$(cat)"

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

case "$file_path" in
    */CLAUDE.md | CLAUDE.md) ;;
    */docs/conventions.md | docs/conventions.md) ;;
    *) exit 0 ;;  # not a guarded file
esac

# Write uses .content; Edit uses .new_string.
content="$(printf '%s' "$input" | jq -r '.tool_input.content // .tool_input.new_string // empty')"

pattern='^##[[:space:]].*\(20[0-9]{2}-[0-9]{2}-[0-9]{2}\)'

if printf '%s' "$content" | grep -qE "$pattern"; then
    base="$(basename "$file_path")"
    reason="Blocked: this write adds a dated '## ... (YYYY-MM-DD)' section heading to $base. That is the exact regression CLAUDE.md was split to prevent on 2026-09-14 (see claudemd_redesign.md and docs/conventions.md's \"Maintaining CLAUDE.md\" entry). Put this content in its journal/v0-6/refactoring/*.md design doc plus one line in journal/CHANGELOG.md instead."
    jq -n --arg reason "$reason" \
        '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
    exit 0
fi

exit 0
