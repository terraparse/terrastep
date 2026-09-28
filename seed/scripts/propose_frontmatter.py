"""Propose frontmatter for every document under journal/ that has none, then apply it.

Two steps, so the owner reviews before anything changes:

  venv/bin/python scripts/propose_frontmatter.py            # write the proposal table (touches no doc)
  ... owner reads and edits journal/misc/status_migration_proposal.md ...
  venv/bin/python scripts/propose_frontmatter.py --apply    # prepend the reviewed frontmatter

The proposal reads each doc's `**Status: ...**` line and, failing that, git
history. It only guesses. Every row carries the basis for the guess and a flag
when the guess is weak. `--apply` reads the table back, validates every value
with scripts/rfc_lib.py, and refuses a doc that already has frontmatter.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rfc_lib  # noqa: E402

PROPOSAL = "journal/misc/status_migration_proposal.md"
COLUMNS = ("doc", "type", "status", "closed_reason", "changed", "basis", "flags")

# `**Status: X**` and `**Status (2026-09-21): X**` (a date in parentheses before the colon).
STATUS_LINE_RE = re.compile(r"(?im)^\W{0,4}status\s*(?:\((?P<when>[^)]*)\))?\s*[:—-]\s*\**\s*(?P<rest>.+?)\**\s*$")
DATE_RE = rfc_lib.DATE_RE
NOT_BUILT_RE = re.compile(r"(?i)\bnothing\b[^.]{0,40}\b(implemented|built|changed)\b|\bnot (yet )?(implemented|built)\b")


# `**Date:** 2026-08-26 · **Status:** proposal — nothing implemented · **Extends:** ...` (mid-line).
MIDLINE_STATUS_RE = re.compile(r"\*\*Status:?\*\*:?\s*(?P<rest>[^·\n]+)")


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


def changelog_dates(root: Path) -> dict[str, str]:
    """doc path -> date of its newest CHANGELOG.md line. A linked doc records a finished change."""
    out: dict[str, str] = {}
    path = root / "journal" / "CHANGELOG.md"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", line)
        for link in re.findall(r"`?(journal/[^\s)`\]]+\.md)`?", line):
            if m:
                out.setdefault(link, m.group(1))
    return out


def git_date(root: Path, rel: str) -> str | None:
    out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=root,
                         capture_output=True, text=True).stdout.strip()
    return out or None


def note_state(status: str, reason: str) -> tuple[str, str]:
    """A note is `in-progress` or `closed`. A finished note is closed as a reference; an unfinished one is in-progress."""
    if status in rfc_lib.NOTE_STATES:
        return status, reason
    return ("closed", "reference") if status == "implemented" else ("in-progress", "")


def propose_row(doc: rfc_lib.Doc, root: Path, changelog: dict[str, str]) -> dict[str, str]:
    text = doc.path.read_text(encoding="utf-8")
    line = parse_status_line(text)
    status, reason, flags, pos = guess_status(line)
    has_blockers = any(s.kind == "B" for s in doc.sections)
    is_plan = has_blockers or (doc.rel.startswith("journal/v0-6/refactoring/") and line is not None)
    dtype = "legacy" if is_plan else "note"
    if dtype == "note":
        status, reason = note_state(status, reason)

    no_verdict = line is None or "unrecognised status words" in flags
    if no_verdict and doc.rel in changelog:
        # No usable status line, but CHANGELOG.md links the doc: it records a finished change.
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


def write_proposal(root: Path) -> int:
    docs = [d for d in rfc_lib.scan_docs(root) if d.meta is None]
    changelog = changelog_dates(root)
    rows = [propose_row(d, root, changelog) for d in docs]
    flagged = sum(1 for r in rows if r["flags"])
    lines = [
        "---", "status: in-progress", f"status_changed: {datetime.date.today().isoformat()}", "type: note",
        "next: Owner reviews and edits the table, then runs scripts/propose_frontmatter.py --apply.", "---", "",
        "# Frontmatter migration proposal", "",
        f"**Generated by `scripts/propose_frontmatter.py`. {len(rows)} documents have no frontmatter; "
        f"{flagged} carry a flag.** Nothing has been applied. Edit any cell, then run `--apply`. "
        "Values are checked against `scripts/rfc_lib.py` on apply.", "",
        "How each guess was made: `status` and `closed_reason` from the words of the doc's `**Status: ...**` "
        "line (none: `closed` / `reference`). `type` is `legacy` for a plan (has a Blockers section, or sits "
        "in `journal/v0-6/refactoring/` and has a status line) and `note` for everything else. `changed` is "
        "the first date after the verdict word in the status line, else the last git commit date. A doc with no "
        "usable status line that `journal/CHANGELOG.md` links is proposed `implemented`, dated by that line "
        "(see the `basis` column).", "",
        "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS),
    ]
    lines += ["| " + " | ".join(r[c] for c in COLUMNS) + " |" for r in rows]
    (root / PROPOSAL).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {PROPOSAL}: {len(rows)} rows, {flagged} flagged")
    return 0


def read_proposal(root: Path) -> list[dict[str, str]]:
    rows = []
    for line in (root / PROPOSAL).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| journal/"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS):
            raise SystemExit(f"row has {len(cells)} cells, expected {len(COLUMNS)}: {line[:80]}")
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def apply_proposal(root: Path) -> int:
    rows = read_proposal(root)
    errors: list[str] = []
    for r in rows:
        path = root / r["doc"]
        if not path.exists():
            errors.append(f"{r['doc']}: file does not exist")
        elif rfc_lib.split_frontmatter(path.read_text(encoding="utf-8"))[0] is not None:
            errors.append(f"{r['doc']}: already has frontmatter; refusing to touch it")
        if r["type"] not in rfc_lib.TYPES:
            errors.append(f"{r['doc']}: type {r['type']!r} is not one of {list(rfc_lib.TYPES)}")
        if r["type"] == "note" and r["status"] not in rfc_lib.NOTE_STATES:
            errors.append(f"{r['doc']}: a note is {list(rfc_lib.NOTE_STATES)}, not {r['status']!r}")
        if r["status"] not in rfc_lib.STATES:
            errors.append(f"{r['doc']}: status {r['status']!r} is not one of {list(rfc_lib.STATES)}")
        if r["status"] == "closed" and r["closed_reason"] not in rfc_lib.CLOSED_REASONS:
            errors.append(f"{r['doc']}: closed needs closed_reason in {list(rfc_lib.CLOSED_REASONS)}")
        if not rfc_lib.is_iso_date(r["changed"]):
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="apply the reviewed proposal table")
    ap.add_argument("--root", type=Path, default=rfc_lib.REPO_ROOT, help="repo root (tests use a temp dir)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    return apply_proposal(root) if args.apply else write_proposal(root)


if __name__ == "__main__":
    raise SystemExit(main())
