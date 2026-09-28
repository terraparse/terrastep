"""Tests for the two enforcement hooks around scripts/check_status.sh.

Each test builds a throwaway git repo that holds copies of the scripts and a few
journal docs, then drives the real hook scripts: the git pre-commit hook
(scripts/git-hooks/pre-commit) and the Claude Code Stop hook
(scripts/check_status_stop_hook.sh). Design: journal/misc/status_and_terraparse_rfcs.md.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = ["rfc_lib.py", "check_status.py", "check_status.sh", "build_status.py",
           "check_status_stop_hook.sh", "git-hooks/pre-commit"]

pytestmark = pytest.mark.skipif(
    not (shutil.which("git") and shutil.which("jq") and shutil.which("python3")),
    reason="needs git, jq and python3")

GOOD = "---\nstatus: in-progress\nstatus_changed: 2026-09-24\ntype: note\n---\n\n# A note\n"
BAD = GOOD.replace("status: in-progress", "status: wip")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def build(repo: Path) -> None:
    subprocess.run([sys.executable, "scripts/build_status.py"], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for rel in SCRIPTS:
        dest = tmp_path / "scripts" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / "scripts" / rel, dest)
    (tmp_path / "journal").mkdir()
    (tmp_path / "journal" / "a.md").write_text(GOOD)
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "core.hooksPath", "scripts/git-hooks")
    # Use the interpreter that runs the tests: it has PyYAML, the system python3 may not.
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    wrapper = tmp_path / "venv" / "bin" / "python"  # a symlink would lose the venv's pyvenv.cfg
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    wrapper.chmod(0o755)
    build(tmp_path)
    git(tmp_path, "add", "-A", ".")
    git(tmp_path, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "base")
    return tmp_path


def commit(repo: Path, msg: str = "change") -> subprocess.CompletedProcess:
    return git(repo, "commit", "-q", "-m", msg)


def stop(repo: Path, payload: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([str(repo / "scripts" / "check_status_stop_hook.sh")], cwd=repo, capture_output=True,
                          text=True, input=json.dumps(payload or {}))


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
    git(repo, "add", "journal/a.md")  # STATUS.md is not regenerated or staged
    r = commit(repo)
    assert r.returncode != 0 and "stale-index" in r.stderr


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
    assert "fm-status" in out["reason"] and "build_status.py" in out["reason"]


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
    assert subprocess.run([sys.executable, "scripts/check_status.py"], cwd=repo, capture_output=True).returncode == 1
    assert stop(repo).stdout == ""
