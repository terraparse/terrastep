"""Tests for terrastep.migrate: the guesses, and that apply is safe."""

from __future__ import annotations

from pathlib import Path

from terrastep import core, migrate
from terrastep.config import Config, MigrateConfig

import pytest

CONFIG = Config(migrate=MigrateConfig(changelog="journal/CHANGELOG.md", legacy_dir="journal/v0-6/refactoring/"))


@pytest.mark.parametrize("line,status,reason", [
    ("IMPLEMENTED (2026-09-14). `perry/reporting/reading_list.py`", "implemented", ""),
    ("IMPLEMENTED AND APPLIED 2026-08-16.", "implemented", ""),
    ("BUILT, 2026-09-11. Approved by the owner", "implemented", ""),
    ("PLANNING. Nothing here is implemented. Written 2026-09-01", "planning", ""),
    ("PROPOSAL. Nothing implemented. Requested 2026-08-25", "planning", ""),
    ("SUPERSEDED as the plan by semantic_ranking_upgrades_v2.md", "closed", "superseded"),
    ("REFERENCE. Not a plan", "closed", "reference"),
    ("INDEX. This note decides nothing.", "closed", "reference"),
])
def test_status_words_map_to_a_state(line, status, reason):
    assert migrate.guess_status(line)[:2] == (status, reason)


@pytest.mark.parametrize("line,status", [
    ("IMPLEMENTED 2026-08-20. §§0-7 below are the planning document", "implemented"),
    ("proposed 2026-08-07, **implemented and applied 2026-08-09.", "implemented"),
    ("IMPLEMENTED 2026-08-26.** §10 is the pilot (B1 and B3 closed).", "implemented"),
    ("IMPLEMENTED 2026-08-28. Nothing else changed", "implemented"),
    ("analysis only, 2026-08-07. Nothing changed in code.", "planning"),
])
def test_a_leading_verdict_wins_and_a_later_negation_means_planning(line, status):
    assert migrate.guess_status(line)[0] == status


def test_no_status_line_is_flagged_and_defaults_to_reference():
    status, reason, flags, _ = migrate.guess_status(None)
    assert (status, reason) == ("closed", "reference") and flags == ["no status line"]


def test_unknown_words_are_flagged():
    assert migrate.guess_status("SOMETHING ODD")[2] == ["unrecognised status words"]


def test_the_status_line_is_found_in_bold_and_plain_forms():
    assert migrate.parse_status_line("# T\n\n**Status: BUILT, 2026-09-11.** More\n").startswith("BUILT, 2026-09-11.")
    assert migrate.parse_status_line("# T\n\nStatus: planning\n") == "planning"
    line = migrate.parse_status_line("# T\n\n**Status (2026-09-21): SUPERSEDED as the build plan; kept.**\n")
    assert line.startswith("SUPERSEDED as the build plan") and "2026-09-21" in line
    assert migrate.guess_status(line)[:2] == ("closed", "superseded")
    assert migrate.parse_status_line("# T\n\n**Date:** 2026-08-26 · **Status:** proposal — nothing implemented · **X:** y\n") \
        == "proposal — nothing implemented"
    assert migrate.parse_status_line("# T\n\nno such line\n") is None


def test_the_date_is_the_first_one_after_the_verdict(tmp_path):
    root = make(tmp_path)
    (root / "journal/misc/c.md").write_text("# C\n\n**Status: proposed 2026-08-07, implemented and applied 2026-08-09.**\n")
    migrate.write_proposal(root, CONFIG)
    assert "c.md | note | closed | reference | 2026-08-09" in (root / migrate.proposal_path(CONFIG)).read_text()


def test_a_note_with_no_status_line_that_the_changelog_links_is_closed_as_reference(tmp_path):
    root = make(tmp_path)
    (root / "journal/CHANGELOG.md").write_text("- A change (2026-09-02) — [`journal/v0-6/refactoring/b_spec.md`](journal/v0-6/refactoring/b_spec.md)\n")
    migrate.write_proposal(root, CONFIG)
    text = (root / migrate.proposal_path(CONFIG)).read_text()
    assert "b_spec.md | note | closed | reference | 2026-09-02 | status: CHANGELOG" in text


def test_a_finished_note_is_closed_and_an_unfinished_one_is_in_progress():
    assert migrate.note_state("implemented", "") == ("closed", "reference")
    assert migrate.note_state("planning", "") == ("in-progress", "")
    assert migrate.note_state("closed", "superseded") == ("closed", "superseded")


def make(tmp_path: Path) -> Path:
    d = tmp_path / "journal" / "v0-6" / "refactoring"
    d.mkdir(parents=True)
    (d / "a_plan.md").write_text("# A\n\n**Status: IMPLEMENTED (2026-09-14).**\n\n## Blockers\n\ntext\n")
    (d / "b_spec.md").write_text("# B\n\nno status line here\n")
    (tmp_path / "journal" / "misc").mkdir()
    (tmp_path / "journal" / "misc" / "has_fm.md").write_text("---\nstatus: in-progress\nstatus_changed: 2026-09-01\ntype: note\n---\n\n# C\n")
    return tmp_path


def test_propose_lists_only_docs_without_frontmatter_and_touches_nothing(tmp_path):
    root = make(tmp_path)
    before = {p: p.read_text() for p in (root / "journal").rglob("*.md")}
    assert migrate.write_proposal(root, CONFIG) == 0
    text = (root / migrate.proposal_path(CONFIG)).read_text()
    assert "a_plan.md | legacy | implemented |  | 2026-09-14" in text
    assert "b_spec.md | note | closed | reference" in text  # no status line, no Blockers: a note, flagged
    assert "has_fm.md" not in text.split("| doc |")[1]
    assert all(p.read_text() == t for p, t in before.items())


def test_apply_prepends_frontmatter_that_then_passes_the_frontmatter_rules(tmp_path):
    root = make(tmp_path)
    migrate.write_proposal(root, CONFIG)
    assert migrate.apply_proposal(root, CONFIG) == 0
    docs = core.scan_docs(root, CONFIG)
    failures, _ = core.check_docs(docs, CONFIG)
    assert failures == {}
    assert (root / "journal/v0-6/refactoring/a_plan.md").read_text().startswith("---\nstatus: implemented\n")


def test_apply_refuses_a_bad_cell_and_changes_nothing(tmp_path):
    root = make(tmp_path)
    migrate.write_proposal(root, CONFIG)
    p = root / migrate.proposal_path(CONFIG)
    p.write_text(p.read_text().replace("| implemented |", "| finished |", 1))
    before = {q: q.read_text() for q in (root / "journal").rglob("*.md")}
    assert migrate.apply_proposal(root, CONFIG) == 1
    assert all(q.read_text() == t for q, t in before.items())


def test_apply_twice_refuses_the_second_time(tmp_path):
    root = make(tmp_path)
    migrate.write_proposal(root, CONFIG)
    assert migrate.apply_proposal(root, CONFIG) == 0
    assert migrate.apply_proposal(root, CONFIG) == 1
