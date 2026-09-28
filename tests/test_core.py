"""Negative controls for terrastep.core.

The design is in journal/origin/status_and_terraparse_rfcs.md. Each rule is
tested the same way: start from a fixture that passes, change one thing, and
require the check to fail with exactly that rule's code. A rule whose mutation
does not fail has proved nothing, so the baselines are also required to pass.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from terrastep import core
from terrastep.config import Config

FIXTURES = Path(__file__).parent / "fixtures"
BASELINES = ["0051_design_ok.md"]
CONFIG = Config()  # scan_dirs = ("journal",), the default


def text_of(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        p = tmp_path / "journal" / "misc" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def codes_for(tmp_path: Path, files: dict[str, str], target: str) -> set[str]:
    docs = core.scan_docs(make_repo(tmp_path, files), CONFIG)
    failures, _ = core.check_docs(docs, CONFIG, {f"journal/misc/{target}"})
    return {f.code for fs in failures.values() for f in fs}


def split_sections(text: str) -> tuple[str, list[str]]:
    """Return (everything before the first ## heading, [one string per ## section])."""
    parts: list[str] = [""]
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
        if line.startswith("## ") and not in_fence:
            parts.append("")
        parts[-1] += line
    return parts[0], parts[1:]


def drop_section(text: str, title_prefix: str) -> str:
    pre, secs = split_sections(text)
    kept = [s for s in secs if not s.startswith(f"## {title_prefix}")]
    assert len(kept) == len(secs) - 1, f"no section starts with {title_prefix!r}"
    return pre + "".join(kept)


def move_section(text: str, title_prefix: str, before_prefix: str | None) -> str:
    """Move a section before another one, or to the end if before_prefix is None."""
    pre, secs = split_sections(text)
    moved = next(s for s in secs if s.startswith(f"## {title_prefix}"))
    rest = [s for s in secs if s is not moved]
    if before_prefix is None:
        rest.append(moved)
    else:
        i = next(i for i, s in enumerate(rest) if s.startswith(f"## {before_prefix}"))
        rest.insert(i, moved)
    return pre + "".join(rest)


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times"
    return text.replace(old, new)


# ------------------------------------------------------------ baselines pass

@pytest.mark.parametrize("name", BASELINES)
def test_baseline_passes_with_no_failures_and_no_warnings(tmp_path, name):
    docs = core.scan_docs(make_repo(tmp_path, {name: text_of(name)}), CONFIG)
    failures, warnings = core.check_docs(docs, CONFIG)
    assert failures == {}
    assert warnings == {}


# ------------------------------------------- one mutation, one expected code

DESIGN = "0051_design_ok.md"

MUTATIONS = [
    # id, baseline, mutate(text) -> text, expected codes
    ("fm-missing", DESIGN, lambda t: t.split("---\n", 2)[2], {"fm-missing"}),
    ("fm-yaml", DESIGN, lambda t: replace_once(t, "next: Owner reviews.", "next: one: two"), {"fm-yaml"}),
    ("fm-type", DESIGN, lambda t: replace_once(t, "type: design", "type: plan"), {"fm-type"}),
    ("fm-status", DESIGN, lambda t: replace_once(t, "status: planning", "status: wip"), {"fm-status"}),
    ("fm-status: idea is not a state", DESIGN, lambda t: replace_once(t, "status: planning", "status: idea"),
     {"fm-status"}),
    ("fm-date", DESIGN, lambda t: replace_once(t, "status_changed: 2026-09-23", "status_changed: yesterday"),
     {"fm-date"}),
    ("fm-closed-reason", DESIGN, lambda t: replace_once(t, "status: planning", "status: closed"),
     {"fm-closed-reason"}),
    ("fm-link", DESIGN, lambda t: replace_once(t, "type: design", "type: design\nblocked_by: nonexistent.md"),
     {"fm-link"}),
    ("body-roles: design has neither summary nor motivation", DESIGN,
     lambda t: drop_section(drop_section(t, "What this is"), "Why, in the terms"), {"body-roles"}),
    ("body-roles: motivation section empty and summary missing", DESIGN,
     lambda t: replace_once(drop_section(t, "What this is"),
                            "A check with no passing example proves nothing.\n", ""), {"body-roles"}),
    ("body-order: sequencing missing", DESIGN, lambda t: drop_section(t, "Sequencing"), {"body-order"}),
    ("body-order: recommendations before questions", DESIGN,
     lambda t: move_section(t, "Recommendations", "Questions"), {"body-order"}),
    ("body-order: front section after blockers", DESIGN,
     lambda t: move_section(t, "Verification", "Questions"), {"body-order"}),
    ("body-dated: undated section after sequencing", DESIGN,
     lambda t: replace_once(t, "## 2026-09-24 A dated note", "## A note with no date"), {"body-dated"}),
    ("body-empty: blockers has no items and no None", DESIGN,
     lambda t: re.sub(r"(?s)(## Blockers\n).*?(## Questions)", r"\1\n\2", t), {"body-empty"}),
    ("body-items: duplicate id", DESIGN,
     lambda t: replace_once(t, "**B2 — A blocker", "**B1 — A blocker"), {"body-items"}),
    ("body-items: a Q item inside blockers", DESIGN,
     lambda t: replace_once(t, "**B2 — A blocker", "**Q9 — A blocker"), {"body-items"}),
    ("body-tag: [pending] is not a tag", DESIGN, lambda t: replace_once(t, "[resolved]", "[pending]"), {"body-tag"}),
    ("body-tag: no tag", DESIGN, lambda t: replace_once(t, " [resolved]", ""), {"body-tag"}),
    ("body-tag: two tags", DESIGN, lambda t: replace_once(t, "[resolved]", "[resolved] [open]"), {"body-tag"}),
    ("body-recommend: question with no recommendation", DESIGN,
     lambda t: replace_once(t, "**Recommendation:** answer yes.", "Answer yes."), {"body-recommend"}),
    ("body-r-cover: B2 missing from recommendations", DESIGN,
     lambda t: replace_once(t, "2. Do the second thing first (B2).\n", ""), {"body-r-cover"}),
    ("body-recommend: an open blocker with no recommendation", DESIGN,
     lambda t: replace_once(t, "**Recommendation: do the second thing, first.**", "Do the second thing, first."),
     {"body-recommend"}),
    ("gate-open-blocker: ready with an open blocker", DESIGN,
     lambda t: replace_once(t, "status: planning", "status: ready"), {"gate-open-blocker"}),
    ("gate-open-blocker: in-progress with an open blocker", DESIGN,
     lambda t: replace_once(t, "status: planning", "status: in-progress"), {"gate-open-blocker"}),
    ("body-history: implemented with no history", DESIGN,
     lambda t: replace_once(t, "status: planning", "status: implemented"), {"body-history"}),
]


@pytest.mark.parametrize("label,base,mutate,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_one_mutation_fails_with_exactly_the_expected_code(tmp_path, label, base, mutate, expected):
    mutated = mutate(text_of(base))
    assert mutated != text_of(base), "the mutation changed nothing, so it proves nothing"
    assert codes_for(tmp_path, {base: mutated}, base) == expected


def test_missing_number_prefix_fails(tmp_path):
    name = "design_without_number.md"
    assert codes_for(tmp_path, {name: text_of(DESIGN)}, name) == {"fm-id"}


def test_duplicate_number_fails_on_both_files(tmp_path):
    files = {DESIGN: text_of(DESIGN), "0051_second_doc.md": text_of(DESIGN)}
    assert codes_for(tmp_path, files, DESIGN) == {"fm-id-dup"}
    assert codes_for(tmp_path, files, "0051_second_doc.md") == {"fm-id-dup"}


# ---------------------------------------------- things that must still pass

def test_scope_and_design_are_expected_but_never_required(tmp_path):
    t = drop_section(drop_section(text_of(DESIGN), "What this does not do"), "The design")
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: t}), CONFIG)
    failures, warnings = core.check_docs(docs, CONFIG)
    assert failures == {}
    messages = " ".join(warnings["journal/misc/" + DESIGN])
    assert "'design'" in messages and "'scope'" in messages


def test_recommendations_out_of_item_order_only_warns(tmp_path):
    t = replace_once(text_of(DESIGN), "2. Do the second thing first (B2).\n3. Answer yes (Q1).",
                     "2. Answer yes (Q1).\n3. Do the second thing first (B2).")
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: t}), CONFIG)
    failures, warnings = core.check_docs(docs, CONFIG)
    assert failures == {}
    assert "out of item order" in warnings["journal/misc/" + DESIGN][0]


def test_arrow_form_counts_as_a_recommendation(tmp_path):
    t = replace_once(text_of(DESIGN), "**Recommendation:** answer yes.", "→ **Yes.** Because of the history.")
    assert codes_for(tmp_path, {DESIGN: t}, DESIGN) == set()


def test_a_bare_arrow_is_not_a_recommendation(tmp_path):
    t = replace_once(text_of(DESIGN), "**Recommendation:** answer yes.", "The answer goes a → b.")
    assert codes_for(tmp_path, {DESIGN: t}, DESIGN) == {"body-recommend"}


def test_a_resolved_blocker_needs_no_recommendation_and_no_recommendations_entry(tmp_path):
    t = replace_once(text_of(DESIGN), "**Recommendation:** do the first thing, because of the project's own history.",
                     "Checked, not assumed. No blocker.")
    t = replace_once(t, "1. Do the first thing (B1).\n", "")
    assert codes_for(tmp_path, {DESIGN: t}, DESIGN) == set()


def test_ready_passes_when_every_blocker_is_resolved(tmp_path):
    t = replace_once(replace_once(text_of(DESIGN), "status: planning", "status: ready"), "[open]", "[resolved]")
    assert codes_for(tmp_path, {DESIGN: t}, DESIGN) == set()


def test_implemented_passes_with_a_history_section(tmp_path):
    t = replace_once(text_of(DESIGN), "status: planning", "status: implemented")
    t = replace_once(t, "## 2026-09-24 A dated note", "## What was built (2026-09-24)")
    assert codes_for(tmp_path, {DESIGN: t}, DESIGN) == set()


def test_closed_passes_with_a_reason(tmp_path):
    t = replace_once(text_of(DESIGN), "status: planning", "status: closed\nclosed_reason: rejected")
    assert codes_for(tmp_path, {DESIGN: t}, DESIGN) == set()


def test_legacy_and_note_get_no_body_check(tmp_path):
    junk = "---\nstatus: in-progress\nstatus_changed: 2026-01-01\ntype: {t}\n---\n\n# Anything\n\n## Whatever\n\ntext\n"
    for t in ("legacy", "note"):
        name = f"{t}_doc.md"
        assert codes_for(tmp_path, {name: junk.format(t=t)}, name) == set()


@pytest.mark.parametrize("status,codes", [
    ("in-progress", set()), ("closed", set()),
    ("planning", {"fm-status-type"}), ("ready", {"fm-status-type"}), ("implemented", {"fm-status-type"}),
])
def test_a_note_is_in_progress_or_closed(tmp_path, status, codes):
    doc = f"---\nstatus: {status}\nstatus_changed: 2026-09-25\ntype: note\nclosed_reason: reference\n---\n\n# N\n"
    assert codes_for(tmp_path, {"n.md": doc}, "n.md") == codes


def test_a_legacy_doc_may_be_in_any_state_but_idea(tmp_path):
    doc = "---\nstatus: implemented\nstatus_changed: 2026-09-25\ntype: legacy\n---\n\n# L\n"
    assert codes_for(tmp_path, {"l.md": doc}, "l.md") == set()


def test_legacy_and_note_may_carry_a_number(tmp_path):
    junk = "---\nstatus: closed\nclosed_reason: reference\nstatus_changed: 2026-01-01\ntype: legacy\n---\n\n# X\n"
    assert codes_for(tmp_path, {"0007_old_doc.md": junk}, "0007_old_doc.md") == set()


def test_blocked_by_resolves_against_any_scanned_file(tmp_path):
    files = {DESIGN: replace_once(text_of(DESIGN), "type: design", "type: design\nblocked_by: other_note.md"),
             "other_note.md": "---\nstatus: implemented\nstatus_changed: 2026-01-01\ntype: note\n---\n\n# Other\n"}
    assert codes_for(tmp_path, files, DESIGN) == set()


def test_heading_inside_a_code_fence_is_not_a_section(tmp_path):
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: text_of(DESIGN)}), CONFIG)
    assert [s.title for s in docs[0].sections].count("Blockers") == 1


# ------------------------------------------------ warnings never fail a run

def test_unclassified_front_section_warns_but_passes(tmp_path):
    t = replace_once(text_of(DESIGN), "## What this does not do", "## Something unusual\n\ntext\n\n## What this does not do")
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: t}), CONFIG)
    failures, warnings = core.check_docs(docs, CONFIG)
    assert failures == {}
    assert "unclassified front sections" in warnings["journal/misc/" + DESIGN][0]


def test_more_than_the_cap_in_progress_warns(tmp_path):
    def wip(n):
        return f"---\nstatus: in-progress\nstatus_changed: 2026-09-2{n}\ntype: note\n---\n\n# n{n}\n"
    docs = core.scan_docs(make_repo(tmp_path, {f"n{i}.md": wip(i) for i in range(4)}), CONFIG)
    failures, warnings = core.check_docs(docs, CONFIG)
    assert failures == {}
    assert f"cap is {CONFIG.in_progress_cap}" in warnings["(all)"][0]


def test_bare_section_only_warns_when_configured_on(tmp_path):
    t = replace_once(text_of(DESIGN), "**Recommendation:** answer yes.", "See §3 for more.")
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: t}), CONFIG)
    _, warnings = core.check_docs(docs, CONFIG)
    assert "journal/misc/" + DESIGN not in warnings

    on = Config(warn_bare_section=True)
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: t}), on)
    _, warnings = core.check_docs(docs, on)
    assert "bare section" in warnings["journal/misc/" + DESIGN][0]


# ----------------------------------------------- the generated index + CLI

def test_next_id_starts_after_the_floor_and_follows_the_highest(tmp_path):
    docs = core.scan_docs(make_repo(tmp_path, {"plain.md": "# x\n"}), CONFIG)
    assert core.next_id(docs, CONFIG) == 1
    docs = core.scan_docs(make_repo(tmp_path, {DESIGN: text_of(DESIGN)}), CONFIG)
    assert core.next_id(docs, CONFIG) == 52
    docs = core.scan_docs(make_repo(tmp_path, {"0007_low.md": "# x\n"}), CONFIG)
    assert core.next_id(docs, CONFIG) == 52  # a low number never lowers the counter


def test_id_floor_is_config_driven(tmp_path):
    docs = core.scan_docs(make_repo(tmp_path, {"plain.md": "# x\n"}), Config(id_floor=48))
    assert core.next_id(docs, Config(id_floor=48)) == 49


def test_index_sorts_newest_first_and_lists_docs_without_frontmatter(tmp_path):
    def doc(day):
        return f"---\nstatus: in-progress\nstatus_changed: 2026-09-{day}\ntype: note\n---\n\n# x\n"
    make_repo(tmp_path, {"old.md": doc("01"), "new.md": doc("20"), "bare.md": "# no frontmatter\n"})
    text = core.render_status(core.scan_docs(tmp_path, CONFIG), CONFIG)
    assert text.index("new.md") < text.index("old.md")
    assert "## No frontmatter yet (1)" in text and "bare.md" in text


def test_index_active_block_holds_only_ready_and_in_progress(tmp_path):
    def doc(status):
        return f"---\nstatus: {status}\nstatus_changed: 2026-09-20\ntype: note\n---\n\n# x\n"
    make_repo(tmp_path, {"a_ready.md": doc("ready"), "b_closed.md": doc("closed")})
    text = core.render_status(core.scan_docs(tmp_path, CONFIG), CONFIG)
    active = text.split("## Active")[1].split("## Planning")[0]
    assert "a_ready.md" in active and "b_closed.md" not in active


def _doc(status, day="20"):
    return f"---\nstatus: {status}\nstatus_changed: 2026-09-{day}\ntype: note\n---\n\n# x\n"


def _blocks(text):
    """Split the index into {heading text: block text}."""
    parts = text.split("\n## ")[1:]
    return {p.split("\n", 1)[0]: p for p in parts}


def test_planning_block_lists_only_planning_docs_newest_first_with_a_count(tmp_path):
    make_repo(tmp_path, {"a_old.md": _doc("planning", "01"), "b_new.md": _doc("planning", "22"),
                         "c_ready.md": _doc("ready"), "d_closed.md": _doc("closed"), "e_done.md": _doc("implemented")})
    blocks = _blocks(core.render_status(core.scan_docs(tmp_path, CONFIG), CONFIG))
    heading = next(h for h in blocks if h.startswith("Planning"))
    assert heading == "Planning — awaiting the owner (2)"
    planning = blocks[heading]
    assert planning.index("b_new.md") < planning.index("a_old.md")
    for other in ("c_ready.md", "d_closed.md", "e_done.md"):
        assert other not in planning


def test_planning_block_sits_between_active_and_all_and_says_so_when_empty(tmp_path):
    make_repo(tmp_path, {"a_ready.md": _doc("ready")})
    text = core.render_status(core.scan_docs(tmp_path, CONFIG), CONFIG)
    assert text.index("## Active") < text.index("## Planning") < text.index("## All")
    assert "Planning — awaiting the owner (0)" in text and "Nothing is in planning." in text


def test_a_doc_in_planning_is_not_in_the_active_block_but_is_still_in_all(tmp_path):
    make_repo(tmp_path, {"p_plan.md": _doc("planning")})
    blocks = _blocks(core.render_status(core.scan_docs(tmp_path, CONFIG), CONFIG))
    assert "p_plan.md" not in blocks["Active (`ready` and `in-progress`)"]
    assert "p_plan.md" in next(v for h, v in blocks.items() if h.startswith("All"))


def test_index_link_is_relative_to_the_first_scan_dirs_entry(tmp_path):
    (tmp_path / "journal" / "plans" / "v0.1").mkdir(parents=True)
    (tmp_path / "journal" / "plans" / "v0.1" / "0001_x.md").write_text(_doc("planning"), encoding="utf-8")
    cfg = Config(scan_dirs=("journal/plans",))
    text = core.render_status(core.scan_docs(tmp_path, cfg), cfg)
    assert "(v0.1/0001_x.md)" in text


def test_scan_dirs_only_reads_designated_directories(tmp_path):
    (tmp_path / "journal" / "plans").mkdir(parents=True)
    (tmp_path / "journal" / "origin").mkdir(parents=True)
    (tmp_path / "journal" / "plans" / "0001_x.md").write_text(_doc("planning"), encoding="utf-8")
    (tmp_path / "journal" / "origin" / "untracked.md").write_text("no frontmatter, not scanned\n", encoding="utf-8")
    docs = core.scan_docs(tmp_path, Config(scan_dirs=("journal/plans",)))
    assert [d.rel for d in docs] == ["journal/plans/0001_x.md"]
