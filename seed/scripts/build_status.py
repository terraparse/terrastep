"""Generate journal/STATUS.md from the frontmatter of every document.

Format: journal/misc/status_and_terraparse_rfcs.md. Nobody edits STATUS.md by
hand; scripts/check_status.py fails when it is stale.

Usage:
  venv/bin/python scripts/build_status.py            # write journal/STATUS.md
  venv/bin/python scripts/build_status.py --stdout   # print, write nothing
  venv/bin/python scripts/build_status.py --next-id  # print the next free RFC number
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rfc_lib  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stdout", action="store_true", help="print the index instead of writing it")
    ap.add_argument("--next-id", action="store_true", help="print the next free RFC number and exit")
    ap.add_argument("--root", type=Path, default=rfc_lib.REPO_ROOT, help="repo root (tests use a temp dir)")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    docs = rfc_lib.scan_docs(root)
    if args.next_id:
        print(f"{rfc_lib.next_id(docs):04d}")
        return 0
    text = rfc_lib.render_status(docs)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    out = root / rfc_lib.SCAN_ROOT / "STATUS.md"
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out.relative_to(root)} ({len(docs)} documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
