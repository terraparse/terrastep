"""Pre-commit enforcement and the "check if changed" logic used by the Stop hook shim."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config as config_mod
from . import core

PRE_COMMIT_HOOK = ".git/hooks/pre-commit"


def git_root(root: Path) -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                          capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def has_uncommitted_changes(root: Path, config: config_mod.Config) -> bool:
    out = subprocess.run(["git", "status", "--porcelain", "--", *config.scan_dirs],
                          cwd=root, capture_output=True, text=True)
    return bool(out.stdout.strip())


def check_snapshot(root: Path, config: config_mod.Config) -> tuple[bool, str]:
    """Run the same check `terrastep check` runs, against `root`. Returns (ok, message)."""
    docs = core.scan_docs(root, config)
    failures, warnings = core.check_docs(docs, config)
    index_path = root / config.index_rel_path
    expected = core.render_status(docs, config)
    if not index_path.exists() or index_path.read_text(encoding="utf-8") != expected:
        failures.setdefault(config.index_rel_path, []).append(core.Finding(
            "stale-index", "index file is missing or differs from the frontmatter; run `terrastep build`"))

    lines: list[str] = []
    for rel, items in sorted(warnings.items()):
        lines += [f"WARN: {rel}: {w}" for w in items]
    for rel, items in sorted(failures.items()):
        lines += [f"FAIL: {rel}: {f}" for f in items]
    if failures:
        lines.append("\n" + core.failure_summary(failures, len(docs), config))
        return False, "\n".join(lines)
    lines.append(f"OK: {len(docs)} document(s) pass ({sum(len(v) for v in warnings.values())} warning(s)).")
    return True, "\n".join(lines)


def precommit(root: Path, config: config_mod.Config) -> tuple[bool, str]:
    """Check the STAGED snapshot, not the working tree, so an unstaged fix cannot hide a bad commit."""
    touched = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD", "--", *config.scan_dirs],
        cwd=root, capture_output=True, text=True).stdout.strip()
    if not touched:
        return True, ""

    snapshot = Path(tempfile.mkdtemp(prefix="terrastep-precommit-"))
    try:
        for scan_dir in config.scan_dirs:
            listed = subprocess.run(["git", "ls-files", "-z", "--", scan_dir], cwd=root,
                                     capture_output=True).stdout
            if listed:
                subprocess.run(["git", "checkout-index", "-z", "--stdin", f"--prefix={snapshot}/"],
                                cwd=root, input=listed, check=True)
        ok, message = check_snapshot(snapshot, config)
        if not ok:
            message = ("Commit blocked: the staged snapshot fails `terrastep check` (see above).\n"
                       "Fix it, then `git add` the fix. If the index is stale, run `terrastep build` "
                       "and stage it.\nTo commit anyway: git commit --no-verify\n\n" + message)
        return ok, message
    finally:
        shutil.rmtree(snapshot, ignore_errors=True)


def install_hooks(root: Path, force: bool = False) -> tuple[bool, str]:
    hook_path = root / PRE_COMMIT_HOOK
    if hook_path.exists() and not force:
        return False, f"{PRE_COMMIT_HOOK} already exists; pass --force to overwrite"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m terrastep hook pre-commit\n', encoding="utf-8")
    hook_path.chmod(0o755)
    return True, f"wrote {PRE_COMMIT_HOOK}"
