#!/usr/bin/env bash
# Checks every document under journal/ against the TerraParse RFC format
# (journal/misc/status_and_terraparse_rfcs.md): frontmatter rules, body rules,
# and that journal/STATUS.md is up to date. Same shape as check_claude_md.sh.
#
# Usage:
#   scripts/check_status.sh            # check everything
#   scripts/check_status.sh FILE ...   # report only these files
#   scripts/check_status.sh --survey   # read-only heading survey
#
# Exit status: 0 if clean, 1 if any rule failed.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

py="$repo_root/venv/bin/python"
[ -x "$py" ] || py="python3"

exec "$py" scripts/check_status.py "$@"
