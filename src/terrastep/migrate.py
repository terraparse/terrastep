"""Propose frontmatter for every document under scan_dirs that has none, then apply it.

Two steps, so the owner reviews before anything changes:

  terrastep migrate propose     # write the proposal table (touches no doc)
  ... owner reads and edits the proposal file ...
  terrastep migrate apply       # prepend the reviewed frontmatter

The proposal reads each doc's `**Status: ...**` line and, failing that, git
history. It only guesses. Every row carries the basis for the guess and a flag
when the guess is weak. `apply` reads the table back, validates every value
against `terrastep.core`, and refuses a doc that already has frontmatter.
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

from . import core
from .config import Config

COLUMNS = ("doc", "type", "status", "closed_reason", "changed", "basis", "flags")

# `**Status: X**` and `**Status (2026-09-21): X**` (a date in parentheses before the colon).
STATUS_LINE_RE = re.compile(r"(?im)^\W{0,4}status\s*(?:\((?P<when>[^)]*)\))?\s*[:—-]\s*\**\s*(?P<rest>.+?)\**\s*$")
DATE_RE = core.DATE_RE
NOT_BUILT_RE = re.compile(r"(?i)\bnothing\b[^.]{0,40}\b(implemented|built|changed)\b|\bnot (yet )?(implemented|built)\b")

# `**Date:** 2026-08-26 · **Status:** proposal — nothing implemented · **Extends:** ...` (mid-line).
MIDLINE_STATUS_RE = re.compile(r"\*\*Status:?\*\*:?\s*(?P<rest>[^·\n]+)")


def proposal_path(config: Config) -> str:
    return f"{config.index_dir}/migration_proposal.md"


def parse_status_line(text: str) -> str | None:
    head = "\n".join(text.splitlines()[:40])
    m = STATUS_LINE_RE.search(head)
    if not m:
        mid = MIDLINE_STATUS_RE.search(head)
        return mid.group("rest").strip() if mid else None
    rest = m.group("rest")
    when = DATE_RE.search(m.group("when") or "")
    # Keep a parenthesised date findable, after the verdict word and without disturbing it.
    return f"{rest} ({when.group(0)})" if when and not DATE_RE.search(rest) else rest


LEADING_CLOSED_RE = re.compile(r"(?i)^\W*(SUPERSEDED|REJECTED|WITHDRAWN|REFERENCE|INDEX|MEASURED AND CLOSED|CLOSED)\b")
LEADING_BUILT_RE = re.compile(r"(?i)^\W*(IMPLEMENTED|BUILT|APPLIED|SHIPPED|LANDED|COMPLETE|DONE)\b")
BUILT_RE = re.compile(r"(?i)\b(IMPLEMENTED|BUILT|APPLIED|SHIPPED|LANDED|COMPLETE|DONE)\b")
PLANNING_RE = re.compile(r"(?i)\b(PLANNING|PROPOSAL|PROPOSED|DRAFT)\b")
CLOSED_ANY_RE = re.compile(r"(?i)\b(SUPERSEDED|REFERENCE|INDEX|CLOSED)\b")
CLOSED_REASON = {"SUPERSEDED": "superseded", "REJECTED": "rejected", "WITHDRAWN": "withdrawn"}


def guess_status(line: str | None) -> tuple[str, str, list[str], int]:
    """Return (status, closed_reason, flags, position of the verdict word) from a status line.

    A verdict at the start of the line wins ("IMPLEMENTED 2026-08-20. ... below are the planning
    document" is implemented). Later, an explicit negation ("Nothing here is implemented") means
    planning, then any built-word means implemented ("proposed ..., implemented and applied").
    """
    if line is None:
        return "closed", "reference", ["no status line"], 0
    if m := LEADING_CLOSED_RE.match(line):
        return "closed", CLOSED_REASON.get(m.group(1).upper(), "reference"), [], m.start()
    if m := LEADING_BUILT_RE.match(line):
        return "implemented", "", [], m.start()
    if m := NOT_BUILT_RE.search(line):
        return "planning", "", [], m.start()
    if m := BUILT_RE.search(line):
        return "implemented", "", [], m.start()
    if m := PLANNING_RE.search(line):
        return "planning", "", [], m.start()
    if m := CLOSED_ANY_RE.search(line):
        return "closed", CLOSED_REASON.get(m.group(1).upper(), "reference"), ["closed word not at the start"], m.start()
    return "closed", "reference", ["unrecognised status words"], 0


def changelog_dates(root: Path, config: Config) -> dict[str, str]:
    """doc path -> date of its newest CHANGELOG.md line. A linked doc records a finished change."""
    out: dict[str, str] = {}
    if not config.migrate.changelog:
        return out
    path = root / config.migrate.changelog
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", line)
        for link in re.findall(r"`?([\w./-]+\.md)`?", line):
            if m:
                out.setdefault(link, m.group(1))
    return out


def git_date(root: Path, rel: str) -> str | None:
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=root,
                         capture_output=True, text=True).stdout.strip()
    return out or None


def note_state(status: str, reason: str) -> tuple[str, str]:
    """A note is `in-progress` or `closed`. A finished note is closed as a reference; an unfinished one is in-progress."""
    if status in core.NOTE_STATES:
        return status, reason
    return ("closed", "reference") if status == "implemented" else ("in-progress", "")


def propose_row(doc: core.Doc, root: Path, config: Config, changelog: dict[str, str]) -> dict[str, str]:
    text = doc.path.read_text(encoding="utf-8")
    line = parse_status_line(text)
    status, reason, flags, pos = guess_status(line)
    has_blockers = any(s.kind == "B" for s in doc.sections)
    is_substantive = has_blockers or (config.migrate.legacy_dir is not None
                                      and doc.rel.startswith(config.migrate.legacy_dir)
                                      and line is not None)
    dtype = "legacy" if is_substantive else "note"
    if dtype == "note":
        status, reason = note_state(status, reason)

    no_verdict = line is None or "unrecognised status words" in flags
    if no_verdict and doc.rel in changelog:
        # No usable status line, but the changelog links the doc: it records a finished change.
        status, reason = note_state("implemented", "") if dtype == "note" else ("implemented", "")
        return {"doc": doc.rel, "type": dtype, "status": status, "closed_reason": reason,
                "changed": changelog[doc.rel], "basis": "status: CHANGELOG; date: CHANGELOG", "flags": ""}

    m = (DATE_RE.search(line, pos) or DATE_RE.search(line)) if line else None
    if m:
        changed, date_src = m.group(0), "status line"
    elif (g := git_date(root, doc.rel)):
        changed, date_src = g, "git"
    else:
        changed, date_src = datetime.date.today().isoformat(), "today (untracked)"
    return {"doc": doc.rel, "type": dtype, "status": status, "closed_reason": reason, "changed": changed,
            "basis": f"status: {'line' if line else 'none'}; date: {date_src}", "flags": "; ".join(flags)}


def write_proposal(root: Path, config: Config) -> int:
    docs = [d for d in core.scan_docs(root, config) if d.meta is None]
    changelog = changelog_dates(root, config)
    rows = [propose_row(d, root, config, changelog) for d in docs]
    flagged = sum(1 for r in rows if r["flags"])
    path = proposal_path(config)
    lines = [
        "---", "status: in-progress", f"status_changed: {datetime.date.today().isoformat()}", "type: note",
        "next: Owner reviews and edits the table, then runs `terrastep migrate apply`.", "---", "",
        "# Frontmatter migration proposal", "",
        f"**Generated by `terrastep migrate propose`. {len(rows)} documents have no frontmatter; "
        f"{flagged} carry a flag.** Nothing has been applied. Edit any cell, then run `terrastep migrate apply`. "
        "Values are checked against `terrastep.core` on apply.", "",
        "How each guess was made: `status` and `closed_reason` from the words of the doc's `**Status: ...**` "
        "line (none: `closed` / `reference`). `type` is `legacy` for a plan (has a Blockers section, or sits "
        "under `[migrate] legacy_dir` and has a status line) and `note` for everything else. `changed` is "
        "the first date after the verdict word in the status line, else the last git commit date. A doc with no "
        "usable status line that `[migrate] changelog` links is proposed `implemented`, dated by that line "
        "(see the `basis` column).", "",
        "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS),
    ]
    lines += ["| " + " | ".join(r[c] for c in COLUMNS) + " |" for r in rows]
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}: {len(rows)} rows, {flagged} flagged")
    return 0


def read_proposal(root: Path, config: Config) -> list[dict[str, str]]:
    rows = []
    for line in (root / proposal_path(config)).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS) or cells[0] == "doc" or set(cells[0]) == {"-"}:
            continue
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def apply_proposal(root: Path, config: Config) -> int:
    rows = read_proposal(root, config)
    errors: list[str] = []
    for r in rows:
        path = root / r["doc"]
        if not path.exists():
            errors.append(f"{r['doc']}: file does not exist")
        elif core.split_frontmatter(path.read_text(encoding="utf-8"))[0] is not None:
            errors.append(f"{r['doc']}: already has frontmatter; refusing to touch it")
        if r["type"] not in core.TYPES:
            errors.append(f"{r['doc']}: type {r['type']!r} is not one of {list(core.TYPES)}")
        if r["type"] == "note" and r["status"] not in core.NOTE_STATES:
            errors.append(f"{r['doc']}: a note is {list(core.NOTE_STATES)}, not {r['status']!r}")
        if r["status"] not in core.STATES:
            errors.append(f"{r['doc']}: status {r['status']!r} is not one of {list(core.STATES)}")
        if r["status"] == "closed" and r["closed_reason"] not in core.CLOSED_REASONS:
            errors.append(f"{r['doc']}: closed needs closed_reason in {list(core.CLOSED_REASONS)}")
        if not core.is_iso_date(r["changed"]):
            errors.append(f"{r['doc']}: changed {r['changed']!r} is not a YYYY-MM-DD date")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(f"\nNothing applied: {len(errors)} problem(s).", file=sys.stderr)
        return 1
    for r in rows:
        block = ["---", f"status: {r['status']}", f"status_changed: {r['changed']}", f"type: {r['type']}"]
        if r["status"] == "closed":
            block.append(f"closed_reason: {r['closed_reason']}")
        block += ["---", "", ""]
        path = root / r["doc"]
        path.write_text("\n".join(block) + path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"prepended frontmatter to {len(rows)} documents")
    return 0
