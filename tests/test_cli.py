"""Tests for terrastep.cli: verbs, exit codes, config lookup. New for the package port."""

from __future__ import annotations

from pathlib import Path

from terrastep import cli

GOOD = "---\nstatus: in-progress\nstatus_changed: 2026-09-24\ntype: note\n---\n\n# A note\n"
BAD = GOOD.replace("status: in-progress", "status: wip")


def make(tmp_path: Path, scan_dir: str = "journal") -> Path:
    (tmp_path / scan_dir).mkdir(parents=True)
    (tmp_path / scan_dir / "a.md").write_text(GOOD, encoding="utf-8")
    return tmp_path


def test_check_fails_without_a_built_index(tmp_path, capsys):
    root = make(tmp_path)
    assert cli.main(["check", "--root", str(root)]) == 1
    assert "stale-index" in capsys.readouterr().err


def test_build_then_check_passes(tmp_path, capsys):
    root = make(tmp_path)
    assert cli.main(["build", "--root", str(root)]) == 0
    assert cli.main(["check", "--root", str(root)]) == 0
    assert "OK" in capsys.readouterr().out


def test_check_exit_code_is_1_on_a_rule_failure(tmp_path):
    root = make(tmp_path)
    (root / "journal" / "a.md").write_text(BAD, encoding="utf-8")
    cli.main(["build", "--root", str(root)])
    (root / "journal" / "a.md").write_text(BAD, encoding="utf-8")
    assert cli.main(["check", "--root", str(root)]) == 1


def test_build_stdout_writes_nothing(tmp_path, capsys):
    root = make(tmp_path)
    assert cli.main(["build", "--root", str(root), "--stdout"]) == 0
    out = capsys.readouterr().out
    assert "Status of every document under journal/" in out
    assert not (root / "journal" / "STATUS.md").exists()


def test_next_id_respects_config_id_floor(tmp_path, capsys):
    root = make(tmp_path)
    (root / "terrastep.toml").write_text('scan_dirs = ["journal"]\nid_floor = 48\n', encoding="utf-8")
    assert cli.main(["next-id", "--root", str(root)]) == 0
    assert capsys.readouterr().out.strip() == "0049"


def test_scan_dirs_from_config_file_are_honored(tmp_path, capsys):
    root = make(tmp_path, scan_dir="journal/plans")
    (root / "terrastep.toml").write_text('scan_dirs = ["journal/plans"]\n', encoding="utf-8")
    (root / "journal" / "origin").mkdir(parents=True)
    (root / "journal" / "origin" / "untracked.md").write_text("no frontmatter\n", encoding="utf-8")
    assert cli.main(["build", "--root", str(root)]) == 0
    assert cli.main(["check", "--root", str(root)]) == 0
    assert (root / "journal" / "plans" / "STATUS.md").exists()
    assert not (root / "journal" / "STATUS.md").exists()


def test_survey_reports_document_count(tmp_path, capsys):
    root = make(tmp_path)
    assert cli.main(["survey", "--root", str(root)]) == 0
    assert "1 documents under journal" in capsys.readouterr().out


def test_migrate_propose_then_apply(tmp_path, capsys):
    root = tmp_path
    (root / "journal").mkdir()
    (root / "journal" / "no_fm.md").write_text("# No frontmatter\n\nSTATUS: PLANNING.\n", encoding="utf-8")
    assert cli.main(["migrate", "propose", "--root", str(root)]) == 0
    assert (root / "journal" / "migration_proposal.md").exists()
    assert cli.main(["migrate", "apply", "--root", str(root)]) == 0
    assert (root / "journal" / "no_fm.md").read_text(encoding="utf-8").startswith("---\n")


def test_check_if_changed_skips_when_nothing_uncommitted(tmp_path, capsys):
    import subprocess
    root = make(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t",
                     "commit", "-q", "-m", "base"], cwd=root, check=True)
    assert cli.main(["check", "--root", str(root), "--if-changed"]) == 0
    assert capsys.readouterr().out == ""


# The summary line counts index failures apart from document failures. The
# index file is not a scanned document, so counting it as one printed
# "3 failure(s) in 2 of 1 document(s)" (found 2026-09-29).

def test_summary_counts_a_stale_index_apart_from_documents(tmp_path, capsys):
    root = make(tmp_path)
    assert cli.main(["check", "--root", str(root)]) == 1
    err = capsys.readouterr().err
    assert "1 failure(s): 1 in journal/STATUS.md (fix: run `terrastep build`)." in err
    assert "document(s)" not in err


def test_summary_with_a_document_failure_and_a_stale_index(tmp_path, capsys):
    root = make(tmp_path)
    (root / "journal" / "a.md").write_text(BAD, encoding="utf-8")
    assert cli.main(["check", "--root", str(root)]) == 1
    err = capsys.readouterr().err
    assert ("2 failure(s): 1 in 1 of 1 document(s); "
            "1 in journal/STATUS.md (fix: run `terrastep build`).") in err


def test_summary_with_only_a_document_failure(tmp_path, capsys):
    root = make(tmp_path)
    cli.main(["build", "--root", str(root)])
    (root / "journal" / "a.md").write_text(BAD, encoding="utf-8")
    cli.main(["build", "--root", str(root)])
    capsys.readouterr()
    assert cli.main(["check", "--root", str(root)]) == 1
    err = capsys.readouterr().err
    assert "1 failure(s): 1 in 1 of 1 document(s)." in err
    assert "STATUS.md" not in err


# `check FILE` for a FILE that is not a scanned document is a usage error. It
# used to print "OK: 1 document(s) pass" and exit 0 without checking anything
# (found 2026-09-29).

def test_check_rejects_a_file_that_does_not_exist(tmp_path, capsys):
    root = make(tmp_path)
    cli.main(["build", "--root", str(root)])
    missing = root / "journal" / "0099_missing.md"
    assert cli.main(["check", "--root", str(root), str(missing)]) == 2
    captured = capsys.readouterr()
    assert "not a document under journal" in captured.err
    assert str(missing) in captured.err
    assert "OK" not in captured.out


def test_check_rejects_a_file_outside_scan_dirs(tmp_path, capsys):
    root = make(tmp_path, scan_dir="journal/plans")
    (root / "terrastep.toml").write_text('scan_dirs = ["journal/plans"]\n', encoding="utf-8")
    outside = root / "journal" / "origin" / "handoff.md"
    outside.parent.mkdir(parents=True)
    outside.write_text("no frontmatter\n", encoding="utf-8")
    cli.main(["build", "--root", str(root)])
    assert cli.main(["check", "--root", str(root), str(outside)]) == 2
    assert "not a document under journal/plans" in capsys.readouterr().err


def test_check_rejects_a_path_outside_the_root_without_a_traceback(tmp_path, capsys):
    root = make(tmp_path / "repo")
    cli.main(["build", "--root", str(root)])
    elsewhere = tmp_path / "elsewhere.md"
    elsewhere.write_text(GOOD, encoding="utf-8")
    assert cli.main(["check", "--root", str(root), str(elsewhere)]) == 2
    assert str(elsewhere) in capsys.readouterr().err


def test_check_names_every_unknown_file_and_checks_none(tmp_path, capsys):
    root = make(tmp_path)
    cli.main(["build", "--root", str(root)])
    good = root / "journal" / "a.md"
    missing = root / "journal" / "b.md"
    assert cli.main(["check", "--root", str(root), str(good), str(missing)]) == 2
    captured = capsys.readouterr()
    assert str(missing) in captured.err and str(good) not in captured.err
    assert "OK" not in captured.out


def test_check_a_scanned_file_still_passes(tmp_path, capsys):
    root = make(tmp_path)
    cli.main(["build", "--root", str(root)])
    assert cli.main(["check", "--root", str(root), str(root / "journal" / "a.md")]) == 0
    assert "OK: 1 document(s) pass" in capsys.readouterr().out


# Brain budget (0003): [brain_budget] configuration, ConfigError -> exit 2,
# and `terrastep design budget`.

def test_a_config_error_exits_2_before_any_document_is_read(tmp_path, capsys):
    root = make(tmp_path)
    (root / "terrastep.toml").write_text(
        'scan_dirs = ["journal"]\n\n[brain_budget]\nenable = true\n', encoding="utf-8")
    assert cli.main(["check", "--root", str(root)]) == 2
    captured = capsys.readouterr()
    assert "configuration error" in captured.err
    assert "enable" in captured.err
    assert "OK" not in captured.out and "FAIL" not in captured.err


def test_a_config_error_exits_2_for_build_too(tmp_path, capsys):
    root = make(tmp_path)
    (root / "terrastep.toml").write_text(
        'scan_dirs = ["journal"]\n\n[brain_budget.limits]\nword_count = -1\n', encoding="utf-8")
    assert cli.main(["build", "--root", str(root)]) == 2


def test_design_budget_works_and_exits_0_with_brain_budget_off(tmp_path, capsys):
    root = make(tmp_path)
    assert cli.main(["design", "budget", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "enabled: False" in out
    assert "policy_id: sha256:4a30b1da8ac7" in out
    assert "schema_version: sha256:6c16c11afcf0" in out


def test_design_budget_json_marks_unset_limits_as_defaults(tmp_path, capsys):
    root = make(tmp_path)
    (root / "terrastep.toml").write_text(
        'scan_dirs = ["journal"]\n\n[brain_budget]\nenabled = true\n\n'
        '[brain_budget.limits]\nword_count = 2500\n', encoding="utf-8")
    assert cli.main(["design", "budget", "--root", str(root), "--format", "json"]) == 0
    import json
    result = json.loads(capsys.readouterr().out)
    assert result["enabled"] is True
    assert result["limits"]["word_count"] == 2500
    assert set(result["defaults"]) == {"evaluative_count", "dependency_edge_count",
                                        "largest_coupled_cluster_size"}
    assert result["policy_id"] == "sha256:cfd3b3f6f3d5"
    assert result["terrastep_version"]


# `terrastep design precheck` (0004): the declarations stage.

from terrastep import budget as budget_mod_for_tests
from terrastep.config import BudgetLimits as _BudgetLimits

_SV = budget_mod_for_tests.schema_version()
_PID = budget_mod_for_tests.policy_id(_BudgetLimits())

_DESIGN_BODY = """## Summary

s

## Blockers

### B1 — a blocker [open]

**Recommendation:** r1.

## Questions

### Q1 — a question

**Recommendation:** r2.

### Q2 — another question

**Recommendation:** r3.

## Recommendations

B1, Q1, Q2.

## Sequencing

do it.
"""


def _design_doc(edges="[]") -> str:
    return (f"---\nstatus: planning\nstatus_changed: 2026-09-29\ntype: design\nnext: x\n"
            f"brain_budget:\n  schema_version: {_SV}\n  policy_id: {_PID}\n"
            f"  depends_on: []\n  edges: {edges}\n---\n# A design\n\n{_DESIGN_BODY}")


def _bb_root(tmp_path: Path, enabled: bool = True, edges: str = "[]") -> Path:
    (tmp_path / "journal" / "plans").mkdir(parents=True)
    (tmp_path / "journal" / "plans" / "0001_x.md").write_text(_design_doc(edges), encoding="utf-8")
    toml = 'scan_dirs = ["journal/plans"]\n' + (
        "[brain_budget]\nenabled = true\n" if enabled else "")
    (tmp_path / "terrastep.toml").write_text(toml, encoding="utf-8")
    return tmp_path


def test_precheck_refuses_when_brain_budget_is_off(tmp_path, capsys):
    root = _bb_root(tmp_path, enabled=False)
    assert cli.main(["design", "precheck", str(root / "journal/plans/0001_x.md"),
                      "--root", str(root)]) == 1
    assert "not enabled" in capsys.readouterr().err


def test_precheck_exit_2_for_a_file_outside_scan_dirs(tmp_path, capsys):
    root = _bb_root(tmp_path)
    outside = tmp_path / "elsewhere.md"
    outside.write_text(_design_doc(), encoding="utf-8")
    assert cli.main(["design", "precheck", str(outside), "--root", str(root)]) == 2
    assert "not a document under journal/plans" in capsys.readouterr().err


def test_precheck_exit_1_for_a_non_design_document(tmp_path, capsys):
    root = _bb_root(tmp_path)
    note = root / "journal" / "plans" / "0002_note.md"
    note.write_text(GOOD, encoding="utf-8")  # type: note
    assert cli.main(["design", "precheck", str(note), "--root", str(root)]) == 1
    assert "not 'design'" in capsys.readouterr().err


def test_precheck_passes_the_worked_example_with_measures_3_2_1(tmp_path, capsys):
    root = _bb_root(tmp_path, edges='[{from: Q1, to: Q2, type: sequencing, contract: c}]')
    target = root / "journal/plans/0001_x.md"
    assert cli.main(["design", "precheck", str(target), "--root", str(root),
                      "--format", "json"]) == 0
    import json
    report = json.loads(capsys.readouterr().out)
    assert report["measures"]["evaluative_count"] == 3
    assert report["measures"]["dependency_edge_count"] == 1
    assert report["measures"]["largest_coupled_cluster_size"] == 1
    assert report["declarations_valid"] is True
    assert report["failures"] == []


def test_precheck_text_output_ok_line(tmp_path, capsys):
    root = _bb_root(tmp_path)
    target = root / "journal/plans/0001_x.md"
    assert cli.main(["design", "precheck", str(target), "--root", str(root)]) == 0
    assert "OK: journal/plans/0001_x.md: declarations valid" in capsys.readouterr().out


def test_precheck_over_budget_exits_0_with_a_warning(tmp_path, capsys):
    edges = ('[{from: B1, to: Q1, type: coupled, contract: c}, '
            '{from: Q1, to: Q2, type: coupled, contract: c}]')
    root = _bb_root(tmp_path, edges=edges)
    (root / "terrastep.toml").write_text(
        'scan_dirs = ["journal/plans"]\n[brain_budget]\nenabled = true\n'
        "[brain_budget.limits]\nlargest_coupled_cluster_size = 2\n", encoding="utf-8")
    pid = budget_mod_for_tests.policy_id(_BudgetLimits(largest_coupled_cluster_size=2))
    target = root / "journal/plans/0001_x.md"
    target.write_text(target.read_text(encoding="utf-8").replace(_PID, pid), encoding="utf-8")
    assert cli.main(["design", "precheck", str(target), "--root", str(root)]) == 0
    err = capsys.readouterr().err
    assert "WARN: journal/plans/0001_x.md: over budget: largest coupled cluster size 3 > 2" in err


def test_precheck_exit_1_on_a_failure(tmp_path, capsys):
    root = _bb_root(tmp_path, edges='[{from: Q1, to: Q9, type: sequencing, contract: c}]')
    target = root / "journal/plans/0001_x.md"
    assert cli.main(["design", "precheck", str(target), "--root", str(root)]) == 1
    assert "FAIL: journal/plans/0001_x.md: [brain-budget-edge]" in capsys.readouterr().err
