"""Tests for the two enforcement hooks: the git pre-commit hook and the Claude
Code Stop hook shim in integrations/claude/stop_hook.sh.

Each test builds a throwaway git repo and drives `terrastep` (the same
interpreter running the tests, via `python -m terrastep`, so no fake venv
wrapper is needed: the installed package carries the interpreter it needs).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
STOP_HOOK = REPO / "integrations" / "claude" / "stop_hook.sh"

pytestmark = pytest.mark.skipif(
    not (shutil.which("git") and shutil.which("jq")),
    reason="needs git and jq")

GOOD = "---\nstatus: in-progress\nstatus_changed: 2026-09-24\ntype: note\n---\n\n# A note\n"
BAD = GOOD.replace("status: in-progress", "status: wip")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def terrastep(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "terrastep", *args], cwd=repo, capture_output=True, text=True)


def build(repo: Path) -> None:
    r = terrastep(repo, "build")
    assert r.returncode == 0, r.stderr


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "journal").mkdir()
    (tmp_path / "journal" / "a.md").write_text(GOOD)
    # The Stop hook shim looks for venv/bin/terrastep; give it a wrapper around
    # the interpreter running these tests, which already has terrastep installed.
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    wrapper = tmp_path / "venv" / "bin" / "terrastep"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m terrastep "$@"\n')
    wrapper.chmod(0o755)
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    r = terrastep(tmp_path, "install-hooks")
    assert r.returncode == 0, r.stderr
    build(tmp_path)
    git(tmp_path, "add", "-A", ".")
    git(tmp_path, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "base")
    return tmp_path


def commit(repo: Path, msg: str = "change") -> subprocess.CompletedProcess:
    return git(repo, "commit", "-q", "-m", msg)


def stop(repo: Path, payload: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(STOP_HOOK)], cwd=repo, capture_output=True, text=True,
                          input=json.dumps(payload or {}))


# ------------------------------------------------------------ pre-commit hook

def test_precommit_allows_a_clean_journal_change(repo):
    (repo / "journal" / "b.md").write_text(GOOD)
    build(repo)
    git(repo, "add", "-A", ".")
    assert commit(repo).returncode == 0


def test_precommit_blocks_a_bad_frontmatter_and_says_why(repo):
    (repo / "journal" / "a.md").write_text(BAD)
    build(repo)
    git(repo, "add", "-A", ".")
    r = commit(repo)
    assert r.returncode != 0
    assert "fm-status" in r.stderr and "Commit blocked" in r.stderr


def test_precommit_blocks_a_stale_index(repo):
    (repo / "journal" / "a.md").write_text(GOOD.replace("2026-09-24", "2026-09-25"))
    git(repo, "add", "journal/a.md")  # the index is not regenerated or staged
    r = commit(repo)
    assert r.returncode != 0 and "stale-index" in r.stderr


def test_precommit_summary_counts_a_stale_index_apart_from_documents(repo):
    # The index file is not a scanned document; counting it as one printed
    # "1 failure(s) in 1 of 1 document(s)" for a clean document (2026-09-29).
    (repo / "journal" / "a.md").write_text(GOOD.replace("2026-09-24", "2026-09-25"))
    git(repo, "add", "journal/a.md")
    r = commit(repo)
    assert "1 failure(s): 1 in journal/STATUS.md (fix: run `terrastep build`)." in r.stderr
    assert "document(s)" not in r.stderr


def test_precommit_checks_the_staged_snapshot_not_the_working_tree(repo):
    (repo / "journal" / "a.md").write_text(BAD)
    build(repo)
    git(repo, "add", "-A", ".")
    (repo / "journal" / "a.md").write_text(GOOD)  # fixed in the working tree, never staged
    build(repo)
    assert commit(repo).returncode != 0, "a bad staged file must not pass because the working tree is fine"


def test_precommit_ignores_a_commit_that_touches_nothing_it_guards(repo):
    # A bad doc is already committed (bypassing the hook). An unrelated commit must not be blocked by it.
    (repo / "journal" / "a.md").write_text(BAD)
    build(repo)
    git(repo, "add", "-A", ".")
    assert git(repo, "commit", "-q", "--no-verify", "-m", "bad, on purpose").returncode == 0
    (repo / "other.txt").write_text("x")
    git(repo, "add", "other.txt")
    assert commit(repo).returncode == 0


def test_no_verify_bypasses_the_hook(repo):
    (repo / "journal" / "a.md").write_text(BAD)
    git(repo, "add", "-A", ".")
    assert git(repo, "commit", "-q", "--no-verify", "-m", "x").returncode == 0


def test_install_hooks_refuses_to_overwrite_without_force(repo):
    assert terrastep(repo, "install-hooks").returncode == 1
    assert terrastep(repo, "install-hooks", "--force").returncode == 0


# ------------------------------------------------------------------ Stop hook

def test_stop_hook_is_silent_when_journal_is_unchanged(repo):
    r = stop(repo)
    assert (r.returncode, r.stdout) == (0, "")


def test_stop_hook_is_silent_when_journal_changed_and_passes(repo):
    (repo / "journal" / "b.md").write_text(GOOD)
    build(repo)
    r = stop(repo)
    assert (r.returncode, r.stdout) == (0, "")


def test_stop_hook_blocks_with_the_failure_when_journal_changed_and_fails(repo):
    (repo / "journal" / "a.md").write_text(BAD)
    r = stop(repo)
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert "fm-status" in out["reason"] and "terrastep build" in out["reason"]


def test_stop_hook_does_not_loop_when_stop_hook_active(repo):
    (repo / "journal" / "a.md").write_text(BAD)
    r = stop(repo, {"stop_hook_active": True})
    assert (r.returncode, r.stdout) == (0, "")


def test_stop_hook_does_not_block_on_a_failure_it_did_not_cause(repo):
    # A bad doc is already committed (bypassing the pre-commit hook). This session changes nothing under journal/.
    (repo / "journal" / "a.md").write_text(BAD)
    build(repo)
    git(repo, "add", "-A", ".")
    assert git(repo, "commit", "-q", "--no-verify", "-m", "bad, on purpose").returncode == 0
    (repo / "notes.txt").write_text("unrelated change")
    assert terrastep(repo, "check").returncode == 1
    assert stop(repo).stdout == ""
