"""Argparse and verb dispatch. No rules."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from pathlib import Path

from . import __version__
from . import budget as budget_mod
from . import config as config_mod
from . import core, hooks, migrate


def _load(args: argparse.Namespace) -> tuple[Path, config_mod.Config]:
    root = args.root.resolve() if args.root else config_mod.find_root()
    cfg = config_mod.load(root, args.config.resolve() if args.config else None)
    return root, cfg


def _add_common(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--root", type=Path, default=None, help="repo root (default: auto-detected)")
    sub.add_argument("--config", type=Path, default=None, help="path to terrastep.toml (default: auto-detected)")


def survey(docs: list[core.Doc], scope: str) -> None:
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
                    unclassified[core.normalize_title(s.title)[:60]] += 1
    print(f"{len(docs)} documents under {scope}")
    print("\nDocuments with a decision section (by heading):")
    for k in "BQRS":
        print(f"  {core.DECISION_NAMES[k]:16s} {decision_docs[k]}")
    print(f"  all four         {len(all_four)}: {all_four}")
    print("\nFront headings matched to a role:")
    for role, n in roles.most_common():
        print(f"  {role:14s} {n}")
    print(f"\nUnclassified headings ({sum(unclassified.values())} total, "
          f"{len(unclassified)} distinct). Most common first:")
    for text, n in unclassified.most_common():
        print(f"  {n:3d}  {text}")


def cmd_check(args: argparse.Namespace) -> int:
    root, cfg = _load(args)
    if args.if_changed and not hooks.has_uncommitted_changes(root, cfg):
        return 0
    docs = core.scan_docs(root, cfg)
    only = None
    if args.files:
        # A named file that is not a scanned document would otherwise be
        # skipped by check_docs and still counted as a pass.
        scanned = {d.rel for d in docs}
        only, unknown = set(), []
        for f in args.files:
            path = Path(f).resolve()
            rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else None
            if rel in scanned:
                only.add(rel)
            else:
                unknown.append(f)
        if unknown:
            print(f"terrastep check: not a document under {'/'.join(cfg.scan_dirs)}: "
                  f"{', '.join(unknown)}", file=sys.stderr)
            return 2
    failures, warnings = core.check_docs(docs, cfg, only)

    if only is None:
        index_path = root / cfg.index_rel_path
        expected = core.render_status(docs, cfg)
        if not index_path.exists() or index_path.read_text(encoding="utf-8") != expected:
            failures.setdefault(cfg.index_rel_path, []).append(core.Finding(
                "stale-index", "index file is missing or differs from the frontmatter; run `terrastep build`"))

    for rel, items in sorted(warnings.items()):
        for w in items:
            print(f"WARN: {rel}: {w}", file=sys.stderr)
    for rel, items in sorted(failures.items()):
        for f in items:
            print(f"FAIL: {rel}: {f}", file=sys.stderr)

    n_docs = len(docs) if only is None else len(only)
    if failures:
        print("\n" + core.failure_summary(failures, n_docs, cfg), file=sys.stderr)
        return 1
    print(f"OK: {n_docs} document(s) pass ({sum(len(v) for v in warnings.values())} warning(s)).")
    return 0


def cmd_survey(args: argparse.Namespace) -> int:
    root, cfg = _load(args)
    docs = core.scan_docs(root, cfg)
    prefixes = tuple(Path(f).resolve().relative_to(root).as_posix() for f in args.dirs)
    survey([d for d in docs if not prefixes or d.rel.startswith(prefixes)], "/".join(cfg.scan_dirs))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    root, cfg = _load(args)
    docs = core.scan_docs(root, cfg)
    text = core.render_status(docs, cfg)
    if args.stdout:
        sys.stdout.write(text)
        return 0
    out = root / cfg.index_rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {cfg.index_rel_path} ({len(docs)} documents)")
    return 0


def cmd_next_id(args: argparse.Namespace) -> int:
    root, cfg = _load(args)
    docs = core.scan_docs(root, cfg)
    print(f"{core.next_id(docs, cfg):04d}")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    root, cfg = _load(args)
    if args.migrate_action == "propose":
        return migrate.write_proposal(root, cfg)
    return migrate.apply_proposal(root, cfg)


def cmd_install_hooks(args: argparse.Namespace) -> int:
    root, _ = _load(args)
    ok, message = hooks.install_hooks(root, force=args.force)
    print(message, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


def cmd_skill_build(args: argparse.Namespace) -> int:
    """Maintainer-only: regenerate this repo's own checked-in generated docs and skill."""
    from . import skilldoc
    pkg_dir = Path(skilldoc.__file__).resolve().parent  # src/terrastep, if this is an editable install
    repo_root = args.root.resolve() if args.root else pkg_dir.parent.parent
    for rel, text in skilldoc.render_all().items():
        path = (pkg_dir if rel.startswith("skill/") else repo_root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    return 0


def cmd_skill_install(args: argparse.Namespace) -> int:
    import shutil
    from importlib.resources import as_file, files

    root, _ = _load(args)
    target = root / ".claude" / "skills" / "terrastep"
    if target.exists() and not args.force:
        print(f"{target.relative_to(root)} already exists; pass --force to overwrite", file=sys.stderr)
        return 1
    with as_file(files("terrastep") / "skill") as bundled:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(bundled, target)
    print(f"installed skill to {target.relative_to(root)}")
    return 0


def cmd_skill(args: argparse.Namespace) -> int:
    return cmd_skill_build(args) if args.skill_action == "build" else cmd_skill_install(args)


def cmd_design_budget(args: argparse.Namespace) -> int:
    """Read-only: report whether brain budget is on, its effective limits, and
    both identity stamps. Works, and exits 0, with brain budget off too."""
    _, cfg = _load(args)
    bb = cfg.brain_budget
    limits_dict = dataclasses.asdict(bb.limits)
    defaults = sorted(config_mod.BUDGET_LIMIT_KEYS - bb.limits_in_file)
    result = {
        "enabled": bb.enabled,
        "max_retries": bb.max_retries,
        "limits": limits_dict,
        "defaults": defaults,
        "policy_id": budget_mod.policy_id(bb.limits),
        "schema_version": budget_mod.schema_version(),
        "terrastep_version": __version__,
    }
    if args.format == "json":
        print(json.dumps(result))
        return 0
    print(f"enabled: {result['enabled']}")
    print(f"max_retries: {result['max_retries']}")
    for key, value in limits_dict.items():
        print(f"  {key}: {value}" + (" (default)" if key in defaults else ""))
    print(f"policy_id: {result['policy_id']}")
    print(f"schema_version: {result['schema_version']}")
    print(f"terrastep version: {__version__}")
    return 0


def cmd_design_precheck(args: argparse.Namespace) -> int:
    """Read-only: the declarations stage (proposal 7.1) for one design
    document — its own frontmatter/body-declaration rules plus the brain
    budget layer's declarations-stage rules. Refuses (exit 1) when brain
    budget is off; exit 2 names FILE if it is not a scanned document."""
    root, cfg = _load(args)
    if not cfg.brain_budget.enabled:
        print("terrastep design precheck: brain budget is not enabled "
              "([brain_budget] enabled = true in terrastep.toml)", file=sys.stderr)
        return 1
    docs = core.scan_docs(root, cfg)
    corpus = {d.name: d for d in docs}
    path = args.file.resolve()
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else None
    doc = next((d for d in docs if d.rel == rel), None)
    if doc is None:
        print(f"terrastep design precheck: not a document under {'/'.join(cfg.scan_dirs)}: "
              f"{args.file}", file=sys.stderr)
        return 2
    if doc.type != "design":
        print(f"terrastep design precheck: {doc.rel} is type {doc.type!r}, not 'design'",
              file=sys.stderr)
        return 1

    names = {d.name for d in docs}
    extra_failures = core.check_frontmatter(doc, names, cfg)
    if doc.meta and not doc.yaml_error:
        body_findings, _body_warnings = core.check_body(doc, cfg)
        extra_failures += [f for f in body_findings if f.code in budget_mod.PRECHECK_BODY_CODES]

    report = budget_mod.precheck_report(doc, corpus, cfg, extra_failures)
    if args.format == "json":
        print(json.dumps(report))
    else:
        for f in report["failures"]:
            print(f"FAIL: {doc.rel}: [{f['code']}] {f['message']}", file=sys.stderr)
        for w in report["warnings"]:
            print(f"WARN: {doc.rel}: {w}", file=sys.stderr)
        if report["declarations_valid"]:
            print(f"OK: {doc.rel}: declarations valid ({len(report['warnings'])} warning(s)).")
        else:
            print(f"\n{len(report['failures'])} failure(s) in the declarations.", file=sys.stderr)
    return 0 if report["declarations_valid"] else 1


def cmd_hook(args: argparse.Namespace) -> int:
    root, cfg = _load(args)
    if args.hook_name != "pre-commit":
        print(f"unknown hook: {args.hook_name}", file=sys.stderr)
        return 1
    ok, message = hooks.precommit(root, cfg)
    if message:
        print(message, file=sys.stderr if not ok else sys.stdout)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="terrastep", description=__doc__)
    sub = ap.add_subparsers(dest="verb", required=True)

    p = sub.add_parser("check", help="check every document under scan_dirs")
    p.add_argument("files", nargs="*", help="report only these files (context still comes from all)")
    p.add_argument("--if-changed", action="store_true",
                    help="exit 0 with no output when scan_dirs has no uncommitted change")
    _add_common(p)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("survey", help="read-only heading survey")
    p.add_argument("dirs", nargs="*", help="path prefixes to narrow the corpus")
    _add_common(p)
    p.set_defaults(func=cmd_survey)

    p = sub.add_parser("build", help="write the index file")
    p.add_argument("--stdout", action="store_true", help="print the index instead of writing it")
    _add_common(p)
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("next-id", help="print the next free document number")
    _add_common(p)
    p.set_defaults(func=cmd_next_id)

    p = sub.add_parser("migrate", help="propose or apply frontmatter for documents that have none")
    p.add_argument("migrate_action", choices=("propose", "apply"))
    _add_common(p)
    p.set_defaults(func=cmd_migrate)

    p = sub.add_parser("install-hooks", help="write the git pre-commit hook")
    p.add_argument("--force", action="store_true", help="overwrite an existing hook")
    _add_common(p)
    p.set_defaults(func=cmd_install_hooks)

    p = sub.add_parser("skill", help="build (maintainer) or install the bundled Claude Code skill")
    p.add_argument("skill_action", choices=("build", "install"))
    p.add_argument("--force", action="store_true", help="overwrite an existing installed skill")
    _add_common(p)
    p.set_defaults(func=cmd_skill)

    p = sub.add_parser("design", help="brain budget: budget, precheck (see also: render, "
                                       "scaffold, added by 0005)")
    design_sub = p.add_subparsers(dest="design_action", required=True)
    pd = design_sub.add_parser("budget", help="show whether brain budget is enabled and its "
                                              "effective limits")
    pd.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    _add_common(pd)
    pd.set_defaults(func=cmd_design_budget)

    pp = design_sub.add_parser("precheck", help="the declarations stage: ledger, edges, "
                                                "evaluation elements, structural measures")
    pp.add_argument("file", type=Path, help="the design document to precheck")
    pp.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    _add_common(pp)
    pp.set_defaults(func=cmd_design_precheck)

    p = sub.add_parser("hook", help="run an installed hook (called by the shim)")
    p.add_argument("hook_name", choices=("pre-commit",))
    _add_common(p)
    p.set_defaults(func=cmd_hook)

    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except config_mod.ConfigError as exc:
        print(f"terrastep: configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
