#!/usr/bin/env bash
# Guards against the exact regression that made CLAUDE.md grow to 5,592
# lines before the 2026-09-14 split (see claudemd_redesign.md and
# docs/conventions.md's "Maintaining CLAUDE.md" entry).
#
# The failure signature: a dated, per-change narrative landing directly in
# the root CLAUDE.md or docs/conventions.md as a "## ... (YYYY-MM-DD)"
# heading, instead of going into a journal/*/refactoring design doc plus a
# one-line journal/CHANGELOG.md entry.
#
# Usage:
#   scripts/check_claude_md.sh            # check the usual two files
#   scripts/check_claude_md.sh FILE ...   # check specific files instead
#
# Exit status: 0 if clean, 1 if a dated section heading was found.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

files=("$@")
if [ "${#files[@]}" -eq 0 ]; then
    files=("CLAUDE.md" "docs/conventions.md")
fi

pattern='^##[[:space:]].*\(20[0-9]{2}-[0-9]{2}-[0-9]{2}\)'
failed=0

for f in "${files[@]}"; do
    [ -f "$f" ] || continue
    if grep -nE "$pattern" "$f" >/dev/null 2>&1; then
        echo "FAIL: $f contains a dated '## ... (YYYY-MM-DD)' section heading:" >&2
        grep -nE "$pattern" "$f" >&2
        echo >&2
        failed=1
    fi
done

if [ "$failed" -ne 0 ]; then
    cat >&2 <<'MSG'
This is the regression CLAUDE.md was split to prevent (claudemd_redesign.md).
A change write-up belongs in its journal/v0-6/refactoring/*.md design doc,
with one line added to journal/CHANGELOG.md pointing at it — not as a new
dated section in CLAUDE.md or docs/conventions.md. See docs/conventions.md's
"Maintaining CLAUDE.md" entry.
MSG
    exit 1
fi

echo "OK: no dated section headings found in: ${files[*]}"
