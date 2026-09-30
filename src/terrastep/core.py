"""Parser and rules for terrastep documents. Reads Config, not constants.

  terrastep check    fails on a document that breaks a rule
  terrastep build     writes the index file from the frontmatter

This module reads files and returns values. It never writes a file.
"""

from __future__ import annotations

import datetime
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import Config

STATES = ("planning", "ready", "in-progress", "implemented", "closed")
# A note is not a proposal, so it is never planned, approved or shipped.
NOTE_STATES = ("in-progress", "closed")
PLAN_TYPES = ("design",)
TYPES = PLAN_TYPES + ("legacy", "note")
CLOSED_REASONS = ("superseded", "rejected", "withdrawn", "reference")

# Every failure code a document can be given, and what it means. The single
# source of truth for `terrastep skill build`'s generated docs (0002) — a test
# (tests/test_core.py) asserts every code string built anywhere in src/terrastep/
# is a key here, and vice versa, so this cannot drift from the rules below.
FAILURE_CODES: dict[str, str] = {
    "fm-missing": "No frontmatter block at the top of the file.",
    "fm-yaml": "The frontmatter block is not valid YAML.",
    "fm-type": "type is missing or not one of the recognized types.",
    "fm-status": "status is missing or not one of the recognized states.",
    "fm-status-type": "A note's status is not in-progress or closed.",
    "fm-date": "status_changed is missing or not a YYYY-MM-DD date.",
    "fm-closed-reason": "status is closed but closed_reason is missing or not recognized.",
    "fm-link": "blocked_by or superseded_by names a document outside the scanned corpus.",
    "fm-id": "A plan-type document's filename has no NNNN_ number prefix.",
    "fm-id-dup": "Two or more documents share the same NNNN number.",
    "body-order": "The four decision sections (Blockers, Questions, Recommendations, "
                  "Sequencing) are missing, duplicated, or out of order.",
    "body-roles": "A required front role (e.g. summary or motivation) has no non-empty section.",
    "body-empty": "Blockers or Questions has no items and doesn't say 'None' with a reason.",
    "body-items": "A blocker/question item is duplicated, misplaced, or malformed.",
    "body-tag": "A blocker's first line doesn't carry exactly one [open] or [resolved] tag.",
    "body-recommend": "An item has no recommendation: a '**Recommendation' run-in or a "
                       "'→ **answer**'.",
    "body-r-cover": "Recommendations doesn't mention every still-open blocker/question by id.",
    "body-dated": "A section after Sequencing has no YYYY-MM-DD date in its heading.",
    "gate-open-blocker": "status is ready or in-progress but a blocker is still [open].",
    "body-history": "status is implemented but no section records what was built.",
    "stale-index": "The index file is missing or doesn't match the current frontmatter.",
    # Brain budget layer (0004), the declarations stage. 0005 adds
    # brain-budget-complexity (the Complexity box, final stage only).
    "brain-budget-ledger-missing": "A design in planning or ready has no brain_budget mapping "
                                   "while brain budget is enabled.",
    "brain-budget-yaml-strict": "brain_budget has a duplicate key, an anchor, alias or merge "
                                "key, a custom tag, or a value that is not a JSON type (for "
                                "example an unquoted date).",
    "brain-budget-schema-version": "schema_version does not match this terrastep's brain "
                                   "budget format. Run `terrastep design render`.",
    "brain-budget-schema": "brain_budget does not match the ledger schema.",
    "brain-budget-policy-id": "policy_id does not match the limits in terrastep.toml. Run "
                              "`terrastep design render`, then check again.",
    "brain-budget-edge": "An edge names an evaluation element that is not in the body, joins "
                        "an evaluation element to itself, or repeats a relationship that is "
                        "already declared.",
    "brain-budget-cycle": "Sequencing edges form a cycle after coupled evaluation elements are "
                         "grouped.",
    "brain-budget-prereq": "A depends_on entry names a file that is not a scanned design "
                          "document, names this file, or repeats another entry.",
    "brain-budget-prereq-cycle": "Designs depend on each other in a cycle.",
    "brain-budget-draft-marker": "A scaffold draft marker is still present.",
    "brain-budget-complexity": "The Complexity box is missing, not placed just before Blockers, "
                              "or not what `terrastep design render` would write.",
}

# Front roles each plan type must have (see "The body" in the design note).
# Each entry is an any-of group: one non-empty section in the group satisfies it.
REQUIRED_ROLES = {
    "design": (("summary", "motivation"),),
}
# Roles a type should have. A missing one warns; it never fails.
EXPECTED_ROLES = {
    "design": ("design", "scope"),
}

# Alias table: normalized heading text -> role. Prefix match. A repo's
# `[aliases]` in terrastep.toml adds patterns to a role; it never removes one.
ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": (r"summary", r"abstract", r"what this is", r"what changed"),
    "motivation": (
        r"motivation", r"why", r"problem", r"context", r"background",
    ),
    "scope": (
        r"what this (?:proposal )?does not", r"what this leaves", r"scope",
        r"goals", r"non-goals", r"no-gos", r"what we are not",
    ),
    "design": (
        r"design", r"shape", r"proposed shape", r"where it plugs",
        r"implementation shape", r"proposal", r"solution", r"specification",
    ),
    "alternatives": (r"options", r"alternatives"),
    "evidence": (
        r"what is true today", r"what exists today", r"findings",
        r"pilot results", r"evidence", r"method",
    ),
    "verification": (
        r"verification", r"tests", r"test plan", r"negative controls",
    ),
    "history": (
        r"what was built", r"implementation (?:record|history)",
        r"execution note",
    ),
    # Tool-owned (0005): only `terrastep design render` writes this section.
    "complexity": (r"complexity",),
}

DECISION_RES = {
    "B": re.compile(r"^blockers\b"),
    "Q": re.compile(r"^(?:open\s+)?questions\b"),
    "R": re.compile(r"^recommendations\b"),
    "S": re.compile(r"^(?:sequencing|sequence|suggested sequence)\b"),
}
DECISION_NAMES = {"B": "Blockers", "Q": "Questions",
                  "R": "Recommendations", "S": "Sequencing"}

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
HEADING2_RE = re.compile(r"^##[ \t]+(.*?)[ \t]*$")
FENCE_RE = re.compile(r"^[ \t]*(```|~~~)")
ITEM_RE = re.compile(r"^(?:#{3,4}[ \t]+|\*\*)([BQ])(\d+)\b")
# An explicit recommendation: a bold "Recommend..." run-in, or the arrow form
# `**Q1 — the question?** → **The answer.**` that real docs use.
RECOMMEND_RE = re.compile(r"\*\*Recommend|→\s*\*\*")
TAG_RE = re.compile(r"\[([A-Za-z-]+)\](?!\()")
# A bare section is a `§N` reference with no document named alongside it.
BARE_SECTION_RE = re.compile(r"(?<!spec )§\s?\d")
ID_FILENAME_RE = re.compile(r"^(\d{4})_")


@dataclass
class Finding:
    code: str
    message: str
    # Set only by the brain budget layer (0004), for a JSON report's precise
    # location (e.g. "brain_budget.edges[1].type") and expected/actual values.
    # Every existing Finding(...) call site is unaffected.
    path: str | None = None
    expected: object | None = None
    actual: object | None = None

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@dataclass
class Section:
    title: str
    kind: str  # "B", "Q", "R", "S" (decision) or "F" (front / other)
    role: str | None
    dated: bool
    lines: list[str]  # body lines under the heading, without the heading


@dataclass
class Item:
    letter: str
    number: int
    first_line: str
    text: str

    @property
    def ident(self) -> str:
        return f"{self.letter}{self.number}"


@dataclass
class Doc:
    path: Path
    rel: str
    meta: dict | None  # None: no frontmatter block at all
    yaml_error: str | None
    body: str
    sections: list[Section] = field(default_factory=list)
    # The raw frontmatter YAML text (0004: budget.py's strict loader composes
    # it), and its character offset in the whole file (0005: `design render`
    # uses it to translate a yaml.compose() node mark back into a file
    # position). Empty/0 when there is no frontmatter block at all.
    fm_text: str = ""
    fm_offset: int = 0

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def type(self) -> str | None:
        return (self.meta or {}).get("type")

    @property
    def status(self) -> str | None:
        return (self.meta or {}).get("status")

    @property
    def rfc_id(self) -> int | None:
        m = ID_FILENAME_RE.match(self.path.name)
        return int(m.group(1)) if m else None

    @property
    def changed(self) -> str:
        return date_text((self.meta or {}).get("status_changed"))


def date_text(value) -> str:
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value) if value is not None else ""


def is_iso_date(value) -> bool:
    if isinstance(value, datetime.date):
        return True
    if isinstance(value, str):
        try:
            datetime.date.fromisoformat(value)
            return True
        except ValueError:
            return False
    return False


def split_frontmatter(text: str) -> tuple[dict | None, str, str | None, str, int]:
    """Return (meta, body, yaml_error, fm_text, fm_offset). meta is None when
    there is no block. fm_text is the raw YAML between the `---` markers
    ("" when there is no block); fm_offset is its character offset in `text`."""
    m = FM_RE.match(text)
    if not m:
        return None, text, None, "", 0
    body = text[m.end():]
    fm_text, fm_offset = m.group(1), m.start(1)
    try:
        meta = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        return {}, body, str(exc).splitlines()[0], fm_text, fm_offset
    if not isinstance(meta, dict):
        return {}, body, "frontmatter is not a key: value mapping", fm_text, fm_offset
    return meta, body, None, fm_text, fm_offset


def normalize_title(title: str) -> str:
    t = DATE_RE.sub("", title).lower().strip()
    t = re.sub(r"^(?:\d+[a-z]?|[a-z]\d+)[.):]?\s+", "", t)  # "7. ", "11a. ", "P1. "
    t = re.sub(r"^[^a-z0-9]+", "", t)
    t = re.sub(r"^(?:the|a|an)\s+", "", t)
    return t


def build_role_patterns(aliases: dict[str, tuple[str, ...]]) -> dict[str, list[re.Pattern]]:
    merged: dict[str, list[str]] = {role: list(pats) for role, pats in ROLE_ALIASES.items()}
    for role, extra in aliases.items():
        merged[role] = merged.get(role, []) + list(extra)
    return {role: [re.compile(rf"^{a}\b") for a in pats] for role, pats in merged.items()}


def classify(title: str, role_patterns: dict[str, list[re.Pattern]]) -> tuple[str, str | None]:
    norm = normalize_title(title)
    for letter, rx in DECISION_RES.items():
        if rx.match(norm):
            return letter, None
    for role, rxs in role_patterns.items():
        if any(rx.match(norm) for rx in rxs):
            return "F", role
    return "F", None


def parse_sections(body: str, role_patterns: dict[str, list[re.Pattern]]) -> list[Section]:
    """Split a body into level-2 sections. Headings inside code fences are text."""
    sections: list[Section] = []
    current: Section | None = None
    in_fence = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        m = None if in_fence else HEADING2_RE.match(line)
        if m:
            title = m.group(1)
            kind, role = classify(title, role_patterns)
            current = Section(title, kind, role, bool(DATE_RE.search(title)), [])
            sections.append(current)
        elif current is not None:
            current.lines.append(line)
    return sections


def parse_items(section: Section) -> list[Item]:
    """Blocker/question items: a `###` heading or a bold run-in starting `B1`/`Q2`."""
    items: list[Item] = []
    lines_by_item: list[list[str]] = []
    in_fence = False
    for line in section.lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
        m = None if in_fence else ITEM_RE.match(line)
        if m:
            items.append(Item(m.group(1), int(m.group(2)), line, ""))
            lines_by_item.append([line])
        elif lines_by_item:
            lines_by_item[-1].append(line)
    for item, lines in zip(items, lines_by_item):
        item.text = "\n".join(lines)
    return items


def decision_items(doc: Doc) -> list[Item]:
    """The blocker/question items check_body counts: parse_items() on each of
    the first Blockers and Questions sections, keeping only an item whose
    letter matches its section (a Q in Blockers is `body-items`' problem, not
    an evaluation element). 0004's measures need this same set, not the raw
    parse — so this is the one place that decides it, and check_body calls it
    too, rather than each computing its own version."""
    dec_idx = {k: [i for i, s in enumerate(doc.sections) if s.kind == k] for k in "BQ"}
    items: list[Item] = []
    for k in "BQ":
        if not dec_idx[k]:
            continue
        sec = doc.sections[dec_idx[k][0]]
        items.extend(i for i in parse_items(sec) if i.letter == k)
    return items


def load_doc(path: Path, root: Path, role_patterns: dict[str, list[re.Pattern]]) -> Doc:
    text = path.read_text(encoding="utf-8")
    meta, body, yaml_error, fm_text, fm_offset = split_frontmatter(text)
    return Doc(path=path, rel=path.relative_to(root).as_posix(), meta=meta,
               yaml_error=yaml_error, body=body, sections=parse_sections(body, role_patterns),
               fm_text=fm_text, fm_offset=fm_offset)


def scan_docs(root: Path, config: Config) -> list[Doc]:
    role_patterns = build_role_patterns(config.aliases)
    excluded = config.excluded_names
    seen: dict[Path, Doc] = {}
    for scan_dir in config.scan_dirs:
        base = root / scan_dir
        for p in sorted(base.rglob("*.md")):
            if p.name in excluded or p in seen:
                continue
            seen[p] = load_doc(p, root, role_patterns)
    return [seen[p] for p in sorted(seen)]


# ---------------------------------------------------------------- the rules

def _has_content(section: Section) -> bool:
    return any(ln.strip() and not ln.lstrip().startswith("#") for ln in section.lines)


def _says_none(section: Section) -> bool:
    text = "\n".join(section.lines)
    return bool(re.search(r"(?im)^\W*none\b", text)) and len(text.split()) >= 6


def is_cleared(item: Item) -> bool:
    """A blocker tagged [resolved] is already decided; it needs no recommendation."""
    return item.letter == "B" and "resolved" in TAG_RE.findall(item.first_line)


def check_frontmatter(doc: Doc, names: set[str], config: Config) -> list[Finding]:
    if doc.meta is None:
        return [Finding("fm-missing", "no frontmatter block at the top of the file")]
    if doc.yaml_error:
        return [Finding("fm-yaml", f"frontmatter does not parse: {doc.yaml_error}")]
    out: list[Finding] = []
    meta = doc.meta
    if meta.get("type") not in TYPES:
        out.append(Finding("fm-type", f"type {meta.get('type')!r} is not one of {list(TYPES)}"))
    if meta.get("status") not in STATES:
        out.append(Finding("fm-status", f"status {meta.get('status')!r} is not one of {list(STATES)}"))
    if meta.get("type") == "note" and meta.get("status") in STATES and meta.get("status") not in NOTE_STATES:
        out.append(Finding("fm-status-type", f"a note is {' or '.join(NOTE_STATES)}, not {meta.get('status')!r}"))
    if not is_iso_date(meta.get("status_changed")):
        out.append(Finding("fm-date", "status_changed is missing or is not a YYYY-MM-DD date"))
    if meta.get("status") == "closed" and meta.get("closed_reason") not in CLOSED_REASONS:
        out.append(Finding("fm-closed-reason",
                           f"status is closed but closed_reason is not one of {list(CLOSED_REASONS)}"))
    scanned = "/".join(config.scan_dirs)
    for key in ("blocked_by", "superseded_by"):
        target = meta.get(key)
        if target is not None and Path(str(target)).name not in names:
            out.append(Finding("fm-link", f"{key} names {target!r}, which is not a document under {scanned}/"))
    if meta.get("type") in PLAN_TYPES and doc.rfc_id is None:
        out.append(Finding("fm-id", "a plan needs a number: name the file NNNN_slug.md "
                                    "(next free number: terrastep next-id)"))
    return out


def check_body(doc: Doc, config: Config) -> tuple[list[Finding], list[str]]:
    """Body rules for the three plan types. Returns (failures, warnings)."""
    out: list[Finding] = []
    warns: list[str] = []
    secs = doc.sections
    dec_idx = {k: [i for i, s in enumerate(secs) if s.kind == k] for k in "BQRS"}

    # Decision sections: exactly one each, in order B Q R S, nothing between them.
    order_ok = True
    for k in "BQRS":
        n = len(dec_idx[k])
        if n == 0:
            out.append(Finding("body-order", f"no {DECISION_NAMES[k]} section"))
            order_ok = False
        elif n > 1:
            out.append(Finding("body-order", f"{n} {DECISION_NAMES[k]} sections; expected one"))
            order_ok = False
    first_dec = min((i for k in "BQRS" for i in dec_idx[k]), default=None)
    if order_ok:
        pos = [dec_idx[k][0] for k in "BQRS"]
        if pos != sorted(pos):
            out.append(Finding("body-order", "decision sections are not in the order Blockers, "
                                             "Questions, Recommendations, Sequencing"))
        else:
            between = [s.title for s in secs[pos[0]:pos[3]] if s.kind == "F"]
            if between:
                out.append(Finding("body-order", f"section(s) between Blockers and Sequencing that are "
                                                 f"not decision sections: {between}"))
            for s in secs[pos[3] + 1:]:
                if not s.dated:
                    out.append(Finding("body-dated", f"section after Sequencing has no YYYY-MM-DD in its "
                                                     f"heading: {s.title!r}"))

    # Front roles required by the type.
    front = secs[:first_dec] if first_dec is not None else secs
    have = {s.role for s in front if s.role and _has_content(s)}
    for group in REQUIRED_ROLES[doc.type]:
        if not have.intersection(group):
            out.append(Finding("body-roles", f"type {doc.type} needs a non-empty "
                                             f"{' or '.join(repr(r) for r in group)} section before the "
                                             f"decision sections"))
    for role in EXPECTED_ROLES[doc.type]:
        if role not in have:
            warns.append(f"type {doc.type} usually has a '{role}' section; none found")
    unclassified = [s.title for s in front if s.kind == "F" and s.role is None]
    if unclassified:
        warns.append(f"unclassified front sections: {unclassified}")

    # Blockers and questions: items, tags, recommendations.
    for k in "BQ":
        if not dec_idx[k]:
            continue
        sec = secs[dec_idx[k][0]]
        sec_items = parse_items(sec)
        wrong = [i.ident for i in sec_items if i.letter != k]
        if wrong:
            out.append(Finding("body-items", f"{wrong} sit in the {DECISION_NAMES[k]} section"))
        sec_items = [i for i in sec_items if i.letter == k]
        if not sec_items and not _says_none(sec):
            out.append(Finding("body-empty", f"{DECISION_NAMES[k]} has no {k}1-style items and does not "
                                             f"say 'None' with a reason"))
    items = decision_items(doc)
    idents = Counter(i.ident for i in items)
    for ident, n in idents.items():
        if n > 1:
            out.append(Finding("body-items", f"{ident} appears {n} times"))
    for item in items:
        if item.letter == "B":
            valid = [t for t in TAG_RE.findall(item.first_line) if t in ("open", "resolved")]
            if len(valid) != 1:
                out.append(Finding("body-tag", f"{item.ident} needs exactly one [open] or [resolved] tag "
                                               f"on its first line"))
        if not is_cleared(item) and not RECOMMEND_RE.search(item.text):
            out.append(Finding("body-recommend", f"{item.ident} has no recommendation: a '**Recommend' "
                                                 f"run-in or a '→ **answer**'"))

    # Recommendations cover every item that still needs a decision. Order is a
    # warning only: real lists sort by priority, not by item number.
    needing = [i for i in items if not is_cleared(i)]
    if dec_idx["R"] and needing:
        r_text = "\n".join(secs[dec_idx["R"][0]].lines)
        last = -1
        for item in needing:
            m = re.search(rf"(?<![A-Za-z0-9]){item.ident}(?![0-9])", r_text)
            if not m:
                out.append(Finding("body-r-cover", f"{item.ident} does not appear in Recommendations"))
            elif m.start() < last:
                warns.append(f"{item.ident} appears in Recommendations out of item order (hint only)")
            else:
                last = m.start()

    # Status rules that read the body.
    if doc.status in ("ready", "in-progress"):
        open_ids = [i.ident for i in items if i.letter == "B"
                    and "open" in TAG_RE.findall(i.first_line)]
        if open_ids:
            out.append(Finding("gate-open-blocker", f"status is {doc.status} but {open_ids} are [open]"))
    if doc.status == "implemented" and not any(s.role == "history" for s in secs):
        out.append(Finding("body-history", "status is implemented but no section records what was built"))

    if config.warn_bare_section and BARE_SECTION_RE.search(doc.body):
        warns.append("bare section reference (§N with no document); hint only")
    return out, warns


def check_doc(doc: Doc, names: set[str], id_counts: Counter, config: Config,
              corpus: dict[str, Doc] | None = None) -> tuple[list[Finding], list[str]]:
    findings = check_frontmatter(doc, names, config)
    warns: list[str] = []
    if doc.rfc_id is not None and id_counts[doc.rfc_id] > 1:
        findings.append(Finding("fm-id-dup", f"number {doc.rfc_id:04d} is used by {id_counts[doc.rfc_id]} files"))
    if doc.meta and not doc.yaml_error and doc.type in PLAN_TYPES:
        body_findings, warns = check_body(doc, config)
        findings.extend(body_findings)
        # The brain budget layer, final stage (0005): only a planning/ready
        # design, only when the repository opted in, and only when the
        # caller supplied the whole corpus (the prerequisite-cycle rule
        # needs every scanned design, not just this file).
        if (config.brain_budget.enabled and doc.status in ("planning", "ready")
                and corpus is not None):
            from . import budget as budget_mod  # deferred: budget.py imports core
            layer = budget_mod.check_layer(doc, corpus, config, stage="final")
            findings.extend(layer.failures)
            warns.extend(layer.warnings)
    if (config.brain_budget.enabled and doc.meta and not doc.yaml_error
            and doc.type in ("note", "legacy") and any(s.kind in ("B", "Q") for s in doc.sections)):
        warns.append(f"a {doc.type} document has a Blockers or Questions section; brain budget "
                     "does not measure it")
    return findings, warns


def check_docs(docs: list[Doc], config: Config,
                only: set[str] | None = None) -> tuple[dict[str, list[Finding]], dict[str, list[str]]]:
    """Check every doc (context comes from all of them); report only `only` if given."""
    names = {d.name for d in docs}
    id_counts = Counter(d.rfc_id for d in docs if d.rfc_id is not None)
    corpus = {d.name: d for d in docs}
    failures: dict[str, list[Finding]] = {}
    warnings: dict[str, list[str]] = {}
    for doc in docs:
        if only is not None and doc.rel not in only:
            continue
        f, w = check_doc(doc, names, id_counts, config, corpus)
        if f:
            failures[doc.rel] = f
        if w:
            warnings[doc.rel] = w
    in_progress = [d.rel for d in docs if d.status == "in-progress"]
    if len(in_progress) > config.in_progress_cap:
        warnings["(all)"] = [f"{len(in_progress)} documents are in-progress; the cap is {config.in_progress_cap}"]
    return failures, warnings


def check_corpus(root: Path, docs: list[Doc], config: Config,
                  only: set[str] | None = None) -> tuple[dict[str, list[Finding]], dict[str, list[str]]]:
    """check_docs(...) plus the stale-index check, in one place so
    `cli.cmd_check` and `hooks.check_snapshot` can never give different
    results (0005)."""
    failures, warnings = check_docs(docs, config, only)
    if only is None:
        index_path = root / config.index_rel_path
        expected = render_status(docs, config)
        if not index_path.exists() or index_path.read_text(encoding="utf-8") != expected:
            failures.setdefault(config.index_rel_path, []).append(Finding(
                "stale-index", "index file is missing or differs from the frontmatter; run `terrastep build`"))
    return failures, warnings


def failure_summary(failures: dict[str, list[Finding]], n_docs: int, config: Config) -> str:
    """The last line of a failing check. The index file is not a scanned
    document, so its failures are counted apart from the documents'."""
    index = config.index_rel_path
    failed_docs = [rel for rel in failures if rel != index]
    parts = []
    if failed_docs:
        n_doc = sum(len(failures[rel]) for rel in failed_docs)
        parts.append(f"{n_doc} in {len(failed_docs)} of {n_docs} document(s)")
    if index in failures:
        parts.append(f"{len(failures[index])} in {index} (fix: run `terrastep build`)")
    total = sum(len(v) for v in failures.values())
    return f"{total} failure(s): {'; '.join(parts)}."


def next_id(docs: list[Doc], config: Config) -> int:
    return max([config.id_floor] + [d.rfc_id for d in docs if d.rfc_id is not None]) + 1


# ------------------------------------------------------------ the index file

def render_status(docs: list[Doc], config: Config, corpus: dict[str, Doc] | None = None) -> str:
    """The text of the index file. Deterministic: no timestamp. `corpus`
    (filename -> Doc) is what the "In budget" column (0005) measures each
    design against; it defaults to one built from `docs` itself, so every
    existing caller that passes only (docs, config) is unaffected."""
    from . import budget as budget_mod  # deferred: budget.py imports core
    if corpus is None:
        corpus = {d.name: d for d in docs}
    with_meta = [d for d in docs if d.meta and not d.yaml_error]
    without = [d for d in docs if not (d.meta and not d.yaml_error)]
    index_dir = config.index_dir

    def link(d: Doc) -> str:
        rel = Path(d.rel)
        try:
            target = rel.relative_to(index_dir)
        except ValueError:
            target = rel  # doc lives outside index_dir; link with the full repo-relative path
        return f"[{d.name}]({target.as_posix()})"

    def row(d: Doc) -> str:
        ident = f"{d.rfc_id:04d}" if d.rfc_id is not None else ""
        nxt = str((d.meta or {}).get("next", "")).replace("|", "\\|").replace("\n", " ")
        in_budget = budget_mod.in_budget_value(d, corpus, config)
        return f"| {d.changed} | {ident} | {link(d)} | {d.type} | {d.status} | {in_budget} | {nxt} |"

    def sort_key(d: Doc):
        return (d.changed, d.rfc_id or 0, d.rel)

    header = ("| Changed | No. | Doc | Type | Status | In budget | Next |\n"
              "|---|---|---|---|---|---|---|")
    ordered = sorted(with_meta, key=sort_key, reverse=True)
    active = [d for d in ordered if d.status in ("ready", "in-progress")]
    planning = [d for d in ordered if d.status == "planning"]

    out = [
        f"<!-- GENERATED by `terrastep build` from each document's frontmatter. Do not edit by hand. -->",
        "",
        f"# Status of every document under {index_dir}/",
        "",
        f"Newest status change first. Regenerate with `terrastep build`.",
        "",
        "## Active (`ready` and `in-progress`)",
        "",
    ]
    out += [header, *[row(d) for d in active]] if active else ["Nothing is ready or in progress."]
    out += ["", f"## Planning — awaiting the owner ({len(planning)})", ""]
    out += [header, *[row(d) for d in planning]] if planning else ["Nothing is in planning."]
    out += ["", f"## All ({len(ordered)} with frontmatter)", "", header, *[row(d) for d in ordered]]
    if without:
        out += ["", f"## No frontmatter yet ({len(without)})", ""]
        out += [f"- {link(d)}" for d in sorted(without, key=lambda d: d.rel)]
    return "\n".join(out) + "\n"
