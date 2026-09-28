"""Reads the two real Perry docs kept under fixtures/perry/ (see "Where each
example goes" in journal/plans/v0.1/0001_python_package_and_cli.md): the
closest real legacy docs to check `survey` and the `legacy` type against.
"""

from __future__ import annotations

from pathlib import Path

from terrastep import cli, core
from terrastep.config import Config

FIXTURES = Path(__file__).parent / "fixtures" / "perry"
CONFIG = Config(scan_dirs=("fixtures/perry",))


def test_both_perry_docs_are_legacy_and_pass_the_check():
    docs = core.scan_docs(Path(__file__).parent, CONFIG)
    assert {d.name for d in docs} == {"resume_stage_shortcuts.md", "s3_prefix_split.md"}
    assert all(d.type == "legacy" for d in docs)
    failures, _ = core.check_docs(docs, CONFIG)
    assert failures == {}


def test_survey_reports_the_real_legacy_docs_by_name(capsys):
    docs = core.scan_docs(Path(__file__).parent, CONFIG)
    cli.survey(docs, "fixtures/perry")
    out = capsys.readouterr().out
    assert "2 documents under fixtures/perry" in out
    assert "history" in out  # both docs have a "## What was built" / "implementation history" section
