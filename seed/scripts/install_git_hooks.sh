#!/usr/bin/env bash
# Point this clone's git at the versioned hooks in scripts/git-hooks/.
# Run once per clone (git does not copy hooks or core.hooksPath on clone).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

chmod +x scripts/git-hooks/*
git config core.hooksPath scripts/git-hooks
echo "core.hooksPath = $(git config core.hooksPath); hooks: $(ls scripts/git-hooks | tr '\n' ' ')"
