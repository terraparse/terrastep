"""Check every document under journal/ against the TerraParse RFC format.

Format: journal/misc/status_and_terraparse_rfcs.md. Rules: scripts/rfc_lib.py.

Usage:
  venv/bin/python scripts/check_status.py            # check all documents + STATUS.md
  venv/bin/python scripts/check_status.py FILE ...   # report only these files
  venv/bin/python scripts/check_status.py --survey [DIR ...]   # read-only heading survey

Exit status: 0 if clean, 1 if any rule failed. Warnings never fail the run.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rfc_lib  # noqa: E402


def survey(docs: list[rfc_lib.Doc]) -> None:
    """Show how every level-2 heading in the corpus classifies. Read-only."""
    roles: Counter = Counter()
    unclassified: Counter = Counter()
    decision_docs = {k: 0 for k in "BQRS"}
    all_four = []
    for doc in docs:
        kinds = {s.kind for s in doc.sections}
        for k in "BQRS":
            decision_docs[k] += k in kinds
        if set("BQRS") <= kinds:
            all_four.append(doc.rel)
        for s in doc.sections:
            if s.kind == "F":
                if s.role:
                    roles[s.role] += 1
                else:
                    unclassified[rfc_lib.normalize_title(s.title)[:60]] += 1
    print(f"{len(docs)} documents under {rfc_lib.SCAN_ROOT}/")
    print("\nDocuments with a decision section (by heading):")
    for k in "BQRS":
        print(f"  {rfc_lib.DECISION_NAMES[k]:16s} {decision_docs[k]}")
    print(f"  all four         {len(all_four)}: {all_four}")
    print("\nFront headings matched to a role:")
    for role, n in roles.most_common():
        print(f"  {role:14s} {n}")
    print(f"\nUnclassified headings ({sum(unclassified.values())} total, "
          f"{len(unclassified)} distinct). Most common first:")
    for text, n in unclassified.most_common():
        print(f"  {n:3d}  {text}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="report only these files (context still comes from all)")
    ap.add_argument("--survey", action="store_true", help="print the heading survey and exit")
    ap.add_argument("--root", type=Path, default=rfc_lib.REPO_ROOT, help="repo root (tests use a temp dir)")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    docs = rfc_lib.scan_docs(root)
    if args.survey:
        # In survey mode the positional arguments are path prefixes to narrow the corpus.
        prefixes = tuple(Path(f).resolve().relative_to(root).as_posix() for f in args.files)
        survey([d for d in docs if not prefixes or d.rel.startswith(prefixes)])
        return 0

    only = None
    if args.files:
        only = {Path(f).resolve().relative_to(root).as_posix() for f in args.files}
    failures, warnings = rfc_lib.check_docs(docs, only)

    if only is None:
        status_path = root / rfc_lib.SCAN_ROOT / "STATUS.md"
        expected = rfc_lib.render_status(docs)
        if not status_path.exists() or status_path.read_text(encoding="utf-8") != expected:
            failures.setdefault(f"{rfc_lib.SCAN_ROOT}/STATUS.md", []).append(rfc_lib.Finding(
                "stale-index", "STATUS.md is missing or differs from the frontmatter; "
                               "run scripts/build_status.py"))

    for rel, items in sorted(warnings.items()):
        for w in items:
            print(f"WARN: {rel}: {w}", file=sys.stderr)
    for rel, items in sorted(failures.items()):
        for f in items:
            print(f"FAIL: {rel}: {f}", file=sys.stderr)

    n_docs = len(docs) if only is None else len(only)
    if failures:
        n = sum(len(v) for v in failures.values())
        print(f"\n{n} failure(s) in {len(failures)} of {n_docs} document(s).", file=sys.stderr)
        return 1
    print(f"OK: {n_docs} document(s) pass ({sum(len(v) for v in warnings.values())} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
