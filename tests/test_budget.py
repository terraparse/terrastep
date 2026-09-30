"""Tests for terrastep.budget: the format definition and its two identity
stamps (0003).

journal/plans/v0.2/0003_brain_budget_config_and_identity.md, Verification,
"Identity": golden values; key order and whitespace do not change policy_id;
each single limit change does; a FORMAT_DEFINITION change changes
schema_version; the working schema's const equals schema_version().
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from terrastep import budget, core
from terrastep.config import BrainBudgetConfig, BudgetLimits, Config

DEFAULT_POLICY_ID = "sha256:4a30b1da8ac7"
WORD_COUNT_2500_POLICY_ID = "sha256:cfd3b3f6f3d5"
FORMAT_SCHEMA_VERSION = "sha256:6c16c11afcf0"


def test_golden_policy_id_for_the_default_limits():
    assert budget.policy_id(BudgetLimits()) == DEFAULT_POLICY_ID


def test_golden_policy_id_with_word_count_2500():
    assert budget.policy_id(BudgetLimits(word_count=2500)) == WORD_COUNT_2500_POLICY_ID


def test_golden_schema_version():
    assert budget.schema_version() == FORMAT_SCHEMA_VERSION


def test_every_single_limit_change_changes_policy_id():
    base = budget.policy_id(BudgetLimits())
    assert budget.policy_id(BudgetLimits(evaluative_count=11)) != base
    assert budget.policy_id(BudgetLimits(dependency_edge_count=12)) != base
    assert budget.policy_id(BudgetLimits(largest_coupled_cluster_size=4)) != base
    assert budget.policy_id(BudgetLimits(word_count=2001)) != base


def test_policy_id_is_insensitive_to_dict_key_order():
    a = budget.identity({"z": 1, "a": 2})
    b = budget.identity({"a": 2, "z": 1})
    assert a == b


def test_a_format_definition_change_changes_schema_version():
    mutated = copy.deepcopy(budget.FORMAT_DEFINITION)
    mutated["draft_marker"] = "<!-- terrastep:different -->"
    assert budget.identity(mutated) != budget.schema_version()


def test_working_schema_const_equals_schema_version():
    schema = budget.working_schema()
    assert schema["properties"]["schema_version"] == {"const": budget.schema_version()}


def test_working_schema_does_not_mutate_base_schema():
    budget.working_schema()
    assert "schema_version" not in budget.BASE_SCHEMA["properties"]


def test_base_schema_still_requires_schema_version():
    # The condition the design records: schema_version() holds only while
    # BASE_SCHEMA["required"] still lists "schema_version" (only the
    # `properties` entry was removed, not the requirement).
    assert "schema_version" in budget.BASE_SCHEMA["required"]


def test_base_schema_has_no_schema_version_property():
    # A schema cannot contain a hash of itself; working_schema() adds this
    # property back once schema_version() is known.
    assert "schema_version" not in budget.BASE_SCHEMA["properties"]


def test_schema_is_json_serializable_and_deterministic():
    # 0004 builds the small schema validator against this shape; here we only
    # confirm the definition is stable, ordinary JSON (no exotic types).
    text_a = json.dumps(budget.working_schema(), sort_keys=True)
    text_b = json.dumps(budget.working_schema(), sort_keys=True)
    assert text_a == text_b


# ---------------------------------------------------------------- 0004 tests
#
# The declarations stage: the strict YAML loader, the schema validator, the
# edge/graph/prerequisite rules, and the three structural measures.
# journal/plans/v0.2/0004_brain_budget_declarations_and_precheck.md,
# Verification.

def _doc(fm_extra: str, body: str, name: str = "0001_x.md", meta_extra: str = "") -> core.Doc:
    """A Doc built the same way core.load_doc would, from literal frontmatter
    + body text, so tests exercise the real yaml.compose()/yaml.safe_load()
    path rather than hand-built dataclasses."""
    text = (f"---\nstatus: planning\nstatus_changed: 2026-09-29\ntype: design\n"
            f"next: x\n{meta_extra}{fm_extra}\n---\n\n{body}")
    meta, body_text, yaml_error, fm_text, fm_offset = core.split_frontmatter(text)
    role_patterns = core.build_role_patterns({})
    return core.Doc(path=Path(name), rel=name, meta=meta, yaml_error=yaml_error, body=body_text,
                     sections=core.parse_sections(body_text, role_patterns),
                     fm_text=fm_text, fm_offset=fm_offset, )


FRONT = """## Summary
s

"""

WORKED_EXAMPLE_BODY = FRONT + """## Blockers

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


def _ledger_yaml(edges="[]", depends_on="[]", policy=None, schema=None) -> str:
    policy = policy or budget.policy_id(BudgetLimits())
    schema = schema or budget.schema_version()
    return (f"brain_budget:\n  schema_version: {schema}\n  policy_id: {policy}\n"
            f"  depends_on: {depends_on}\n  edges: {edges}\n")


def test_schema_keyword_guard():
    """Every dict key BASE_SCHEMA uses at a schema-object position is one of
    the ten supported keywords. `properties`' own keys are field names, not
    keywords, so only its *values* (each a sub-schema) are walked further."""
    allowed = budget._SUPPORTED_SCHEMA_KEYWORDS

    def walk(schema: dict):
        for key, value in schema.items():
            assert key in allowed, f"BASE_SCHEMA uses an unsupported keyword: {key!r}"
            if key == "properties" or key == "$defs":
                for sub_schema in value.values():
                    walk(sub_schema)
            elif key == "items":
                walk(value)
    walk(budget.BASE_SCHEMA)


def test_conformance_with_jsonschema_on_valid_and_invalid_ledgers():
    jsonschema = pytest.importorskip("jsonschema")
    schema = budget.working_schema()
    good = {
        "schema_version": budget.schema_version(), "policy_id": budget.policy_id(BudgetLimits()),
        "depends_on": [{"file": "0007_x.md", "contract": "c"}],
        "edges": [{"from": "Q1", "to": "Q2", "type": "sequencing", "contract": "c"}],
    }
    mutations = [
        good,
        {**good, "edges": [{"from": "Q1", "to": "Q2", "kind": "sequencing", "contract": "c"}]},
        {**good, "edges": [{"from": "Q1", "to": "D2", "type": "sequencing", "contract": "c"}]},
        {**good, "policy_id": "not-a-hash"},
        {**good, "depends_on": [{"file": "x.md", "contract": "c"}]},  # no NNNN_ prefix
        {**good, "extra": "field"},
        {k: v for k, v in good.items() if k != "edges"},  # missing required
    ]
    for ledger in mutations:
        expected = jsonschema.Draft202012Validator(schema).is_valid(ledger)
        actual = len(budget.validate(ledger, schema)) == 0
        assert actual == expected, ledger


@pytest.mark.parametrize("extra,reason_substr", [
    ("a: &x\n    k: 1\n  b: *x", "alias"),
    ("a: &x\n    k: 1\n  c:\n    <<: *x", "merge"),
    ("d: 1\n  d: 2", "duplicate"),
    ("e: 2026-09-28", "timestamp"),
])
def test_strict_yaml_rejects_each_construct_inside_brain_budget(extra, reason_substr):
    doc = _doc(f"brain_budget:\n  {extra}\n", WORKED_EXAMPLE_BODY)
    result = budget.load_ledger(doc)
    assert result.ledger is None
    assert any(reason_substr in r for r in result.strict_errors), result.strict_errors


def test_strict_yaml_leaves_status_changed_alone_even_with_a_bad_construct_inside():
    doc = _doc("brain_budget:\n  d: 1\n  d: 2\n", WORKED_EXAMPLE_BODY)
    assert doc.yaml_error is None
    assert doc.meta["status_changed"].isoformat() == "2026-09-29"


def test_the_same_constructs_outside_brain_budget_keep_todays_behavior():
    doc = _doc(_ledger_yaml() + "other: &x\n  k: 1\nother2: *x\n", WORKED_EXAMPLE_BODY)
    assert doc.yaml_error is None
    assert doc.meta["other2"] == {"k": 1}  # the alias still resolves normally
    result = budget.load_ledger(doc)
    # An alias/anchor outside brain_budget does not fail the strict check;
    # only brain_budget's own subtree is walked.
    assert result.ledger is not None
    assert result.strict_errors == []


def test_edge_with_kind_instead_of_type_fails_schema_with_a_precise_path():
    doc = _doc(_ledger_yaml(edges='[{from: Q1, to: Q2, kind: sequencing, contract: c}]'),
               WORKED_EXAMPLE_BODY)
    corpus = {doc.name: doc}
    result = budget.check_layer(doc, corpus, Config(brain_budget=BrainBudgetConfig(enabled=True)),
                                "declarations")
    codes = {f.code for f in result.failures}
    assert "brain-budget-schema" in codes
    paths = {f.path for f in result.failures if f.code == "brain-budget-schema"}
    assert "brain_budget.edges[0].kind" in paths


def test_edge_to_a_missing_element_fails_brain_budget_edge():
    doc = _doc(_ledger_yaml(edges='[{from: Q1, to: Q3, type: sequencing, contract: c}]'),
               WORKED_EXAMPLE_BODY)
    corpus = {doc.name: doc}
    result = budget.check_layer(doc, corpus, Config(brain_budget=BrainBudgetConfig(enabled=True)),
                                "declarations")
    assert any(f.code == "brain-budget-edge" and f.path == "brain_budget.edges[0].to"
              for f in result.failures)


def test_evaluative_count_counts_open_and_resolved_headings_and_bold_runins():
    body = FRONT + """## Blockers

### B1 — heading style [open]

**Recommendation:** r.

**B2 — bold run-in style [resolved]**

## Questions

### Q1 — a question

**Recommendation:** r.

## Recommendations

B1, B2, Q1.

## Sequencing

s.
"""
    doc = _doc(_ledger_yaml(), body)
    result = budget.check_layer(doc, {doc.name: doc},
                                Config(brain_budget=BrainBudgetConfig(enabled=True)), "declarations")
    assert result.measures["evaluative_count"] == 3


@pytest.mark.parametrize("edges,expected_size,expected_members", [
    # No edges: every one of the 3 real elements (B1, Q1, Q2) is isolated (1),
    # not 0 — 0 is only for a document with no evaluation elements at all.
    ("[]", 1, ["B1"]),
    ('[{from: B1, to: Q1, type: sequencing, contract: c}]', 1, ["B1"]),  # sequencing doesn't enlarge
    ('[{from: B1, to: Q1, type: coupled, contract: c}, '
     '{from: Q1, to: Q2, type: coupled, contract: c}]', 3, ["B1", "Q1", "Q2"]),
])
def test_largest_coupled_cluster_via_check_layer(edges, expected_size, expected_members):
    doc = _doc(_ledger_yaml(edges=edges), WORKED_EXAMPLE_BODY)
    result = budget.check_layer(doc, {doc.name: doc},
                                Config(brain_budget=BrainBudgetConfig(enabled=True)), "declarations")
    assert result.measures["largest_coupled_cluster_size"] == expected_size
    assert result.cluster_members == expected_members


def test_largest_coupled_cluster_is_zero_with_no_evaluation_elements():
    empty_body = FRONT + """## Blockers

None: none needed here at all.

## Questions

None: none needed here at all.

## Recommendations

n/a

## Sequencing

n/a
"""
    doc = _doc(_ledger_yaml(), empty_body)
    result = budget.check_layer(doc, {doc.name: doc},
                                Config(brain_budget=BrainBudgetConfig(enabled=True)), "declarations")
    assert result.measures["evaluative_count"] == 0
    assert result.measures["largest_coupled_cluster_size"] == 0


def test_two_disconnected_coupled_clusters():
    size, members = budget.largest_coupled_cluster(
        ["B1", "B2", "Q1", "Q2"],
        [{"from": "B1", "to": "B2", "type": "coupled"},
         {"from": "Q1", "to": "Q2", "type": "coupled"}])
    assert size == 2 and members in (["B1", "B2"], ["Q1", "Q2"])


def test_a_sequencing_cycle_across_clusters_is_found():
    finding = budget._check_sequencing_cycle(
        ["B1", "Q1", "Q2"],
        [{"from": "B1", "to": "Q1", "type": "sequencing"},
         {"from": "Q1", "to": "Q2", "type": "sequencing"},
         {"from": "Q2", "to": "B1", "type": "sequencing"}])
    assert finding is not None and finding.code == "brain-budget-cycle"


def test_a_prereq_cycle_across_three_designs_fails_on_each(tmp_path):
    sv, pid = budget.schema_version(), budget.policy_id(BudgetLimits())

    def make(name, target):
        text = (f"---\nstatus: planning\nstatus_changed: 2026-09-29\ntype: design\nnext: x\n"
                f"brain_budget:\n  schema_version: {sv}\n  policy_id: {pid}\n"
                f"  depends_on:\n    - file: {target}\n      contract: c\n  edges: []\n---\n"
                f"{FRONT}## Blockers\n\nNone: none needed here.\n\n## Questions\n\n"
                "None: none needed here.\n\n## Recommendations\n\nn/a\n\n## Sequencing\n\nn/a\n")
        (tmp_path / name).write_text(text, encoding="utf-8")

    make("0001_a.md", "0002_b.md")
    make("0002_b.md", "0003_c.md")
    make("0003_c.md", "0001_a.md")
    role_patterns = core.build_role_patterns({})
    docs = {}
    for name in ("0001_a.md", "0002_b.md", "0003_c.md"):
        text = (tmp_path / name).read_text(encoding="utf-8")
        meta, body_text, yaml_error, fm_text, fm_offset = core.split_frontmatter(text)
        docs[name] = core.Doc(path=tmp_path / name, rel=name, meta=meta, yaml_error=yaml_error,
                              body=body_text, sections=core.parse_sections(body_text, role_patterns),
                              fm_text=fm_text, fm_offset=fm_offset)

    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    for name in docs:
        result = budget.check_layer(docs[name], docs, cfg, "declarations")
        assert any(f.code == "brain-budget-prereq-cycle" for f in result.failures), name


def test_measures_are_null_not_zero_when_the_ledger_fails_schema():
    doc = _doc(_ledger_yaml(edges="not-a-list"), WORKED_EXAMPLE_BODY)
    result = budget.check_layer(doc, {doc.name: doc},
                                Config(brain_budget=BrainBudgetConfig(enabled=True)), "declarations")
    assert result.measures["dependency_edge_count"] is None
    assert result.measures["largest_coupled_cluster_size"] is None
    assert result.measures["evaluative_count"] == 3  # unaffected: body-only, no ledger needed


def test_precheck_report_over_budget_gives_zero_exit_and_names_members():
    edges = ('[{from: B1, to: Q1, type: coupled, contract: c}, '
            '{from: Q1, to: Q2, type: coupled, contract: c}]')
    doc = _doc(_ledger_yaml(edges=edges,
                            policy=budget.policy_id(BudgetLimits(largest_coupled_cluster_size=2))),
               WORKED_EXAMPLE_BODY)
    cfg = Config(brain_budget=BrainBudgetConfig(
        enabled=True, limits=BudgetLimits(largest_coupled_cluster_size=2)))
    report = budget.precheck_report(doc, {doc.name: doc}, cfg, [])
    assert report["declarations_valid"] is True
    assert report["structural_in_budget"] is False
    assert report["over_budget"] == [{"measure": "largest_coupled_cluster_size", "actual": 3,
                                      "limit": 2, "members": ["B1", "Q1", "Q2"]}]
    assert report["warnings"] == ["over budget: largest coupled cluster size 3 > 2 (B1, Q1, Q2)"]


def test_precheck_report_on_the_worked_example_measures_3_2_1():
    doc = _doc(_ledger_yaml(edges='[{from: Q1, to: Q2, type: sequencing, contract: c}]'),
              WORKED_EXAMPLE_BODY)
    report = budget.precheck_report(doc, {doc.name: doc},
                                    Config(brain_budget=BrainBudgetConfig(enabled=True)), [])
    assert report["measures"]["evaluative_count"] == 3
    assert report["measures"]["dependency_edge_count"] == 1
    assert report["measures"]["largest_coupled_cluster_size"] == 1
    assert report["measures"]["word_count"] is None
    assert report["declarations_valid"] is True
    assert report["failures"] == []


# ---------------------------------------------------------------- 0005 tests
#
# The Complexity box, render, scaffold, and the final-stage layer.
# journal/plans/v0.2/0005_brain_budget_box_render_scaffold_check.md,
# Verification.

WORKED_EXAMPLE_FULL = """---
status: planning
status_changed: 2026-09-29
type: design
next: Owner reviews.
brain_budget:
  schema_version: {sv}
  policy_id: {pid}
  depends_on:
    - file: 0007_transaction_query_contract.md
      contract: The query returns every authorized, filtered row in the requested sort order.
  edges:
    - from: Q1
      to: Q2
      type: sequencing
      contract: Q2 orders the field set that Q1 selects. The order cannot change which fields Q1 selects.
---
# Add the CSV download

## Summary

Add a CSV download of the transaction view. Rows come from the query contract in 0007_transaction_query_contract.md: every authorized, filtered row, in the requested sort order.

## Scope

This design adds CSV only. It does not change the 0007 query or add other export formats.

## The design

- Read rows through the 0007 query. Do not add a second query path.
- Serialize each row with CSV quoting and escaping, using the Q1 fields in Q2 order.
- Return the result as a CSV attachment.

## Verification

- Compare the exported rows and their order with the same filtered query.
- Cover empty results, quoting and escaping, and rows the caller is not allowed to see.

## Complexity

**Within budget: yes.**

| Measure | Actual | Limit |
| --- | ---: | ---: |
| Evaluative count | 3 | 10 |
| Dependency edge count | 2 | 11 |
| Largest coupled cluster size | 1 | 3 |
| Word count | 245 | 2000 |

## Blockers

### B1 — The response helpers may not stream an attachment [open]

The design assumes that the response helpers can stream a CSV attachment. Nobody has checked this yet.

**Recommendation:** inspect the response helpers before coding. If they cannot stream, add that capability in a separate design first.

## Questions

### Q1 — Which fields does the CSV include?

**Recommendation:** the fields that the transaction view displays.

### Q2 — In what order are the columns written?

**Recommendation:** the on-screen column order when the export starts.

## Recommendations

1. Confirm streaming support before coding (B1).
2. Export the displayed fields (Q1) in their on-screen order (Q2).

## Sequencing

Resolve B1. Then build the serializer and the download in one change.
""".format(sv=budget.schema_version(), pid=budget.policy_id(BudgetLimits()))


def _load_as_doc(text: str, name: str = "0008_csv_download.md") -> core.Doc:
    meta, body_text, yaml_error, fm_text, fm_offset = core.split_frontmatter(text)
    role_patterns = core.build_role_patterns({})
    return core.Doc(path=Path(name), rel=name, meta=meta, yaml_error=yaml_error, body=body_text,
                    sections=core.parse_sections(body_text, role_patterns),
                    fm_text=fm_text, fm_offset=fm_offset)


def test_word_count_on_the_worked_example_is_245():
    doc = _load_as_doc(WORKED_EXAMPLE_FULL)
    assert budget.word_count(doc) == 245


def test_word_count_changes_when_the_prose_changes():
    duplicated = WORKED_EXAMPLE_FULL.replace(
        "The design assumes that the response helpers",
        "The design assumes that the design assumes that the response helpers")
    doc = _load_as_doc(duplicated)
    assert budget.word_count(doc) == 249


def test_word_count_excludes_the_complexity_section():
    doc = _load_as_doc(WORKED_EXAMPLE_FULL)
    body_without_box = WORKED_EXAMPLE_FULL.split("## Complexity")[0]
    assert "Within budget" not in body_without_box  # sanity: box really removed
    # word_count on the SAME doc (box included in the parsed sections) must
    # equal word_count computed with the box already stripped out entirely.
    stripped = WORKED_EXAMPLE_FULL.split("## Complexity")[0] + "## Blockers" + \
        WORKED_EXAMPLE_FULL.split("## Blockers", 1)[1]
    doc_stripped = _load_as_doc(stripped)
    assert budget.word_count(doc) == budget.word_count(doc_stripped)


def test_complexity_box_within_budget_matches_the_proposals_exact_text():
    measures = {"evaluative_count": 3, "dependency_edge_count": 2,
                "largest_coupled_cluster_size": 1, "word_count": 245}
    limits = {"evaluative_count": 10, "dependency_edge_count": 11,
              "largest_coupled_cluster_size": 3, "word_count": 2000}
    box = budget.complexity_box(measures, limits, [], True)
    assert box == (
        "## Complexity\n\n**Within budget: yes.**\n\n"
        "| Measure | Actual | Limit |\n| --- | ---: | ---: |\n"
        "| Evaluative count | 3 | 10 |\n| Dependency edge count | 2 | 11 |\n"
        "| Largest coupled cluster size | 1 | 3 |\n| Word count | 245 | 2000 |\n")


def test_complexity_box_over_budget_matches_the_proposals_exact_text():
    measures = {"evaluative_count": 4, "dependency_edge_count": 5,
                "largest_coupled_cluster_size": 4, "word_count": 100}
    limits = {"evaluative_count": 10, "dependency_edge_count": 11,
              "largest_coupled_cluster_size": 3, "word_count": 2000}
    box = budget.complexity_box(measures, limits, ["B1", "Q1", "Q2", "Q3"], False)
    assert box.startswith(
        "## Complexity\n\n**Within budget: no.** Over: largest coupled cluster size 4 > 3 "
        "(B1, Q1, Q2, Q3).\n\n")


def test_render_is_idempotent_on_an_already_correct_file():
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    out = budget.render(WORKED_EXAMPLE_FULL, cfg)
    assert out == WORKED_EXAMPLE_FULL  # already correct: no change at all
    out2 = budget.render(out, cfg)
    assert out2 == out


def test_render_replaces_stamps_in_place_and_keeps_sibling_bytes():
    stale = WORKED_EXAMPLE_FULL.replace(budget.schema_version(), "sha256:000000000000")
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    out = budget.render(stale, cfg)
    assert budget.schema_version() in out
    assert "sha256:000000000000" not in out
    # Every sibling key/comment/line outside the two stamp values and the box
    # is untouched: the ledger's depends_on/edges block is byte-identical.
    assert ("depends_on:\n    - file: 0007_transaction_query_contract.md\n"
           "      contract: The query returns every authorized, filtered row "
           "in the requested sort order.\n  edges:\n    - from: Q1\n") in out


def test_render_adopts_a_planning_design_with_no_ledger():
    text = """---
status: planning
status_changed: 2026-09-29
type: design
next: x
---
# T

## Summary
s

## Blockers
None: none needed here at all.

## Questions
None: none needed here at all.

## Recommendations
n/a

## Sequencing
n/a
"""
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    out = budget.render(text, cfg)
    assert budget.schema_version() in out and budget.policy_id(BudgetLimits()) in out
    assert "## Complexity" in out
    doc = _load_as_doc(out, "t.md")
    assert doc.meta["brain_budget"]["depends_on"] == []
    assert doc.meta["brain_budget"]["edges"] == []


@pytest.mark.parametrize("mutate,reason_substr", [
    (lambda t: t, None),  # control: unmutated, must succeed
])
def test_render_succeeds_as_a_control(mutate, reason_substr):
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    budget.render(mutate(WORKED_EXAMPLE_FULL), cfg)  # must not raise


def test_render_refuses_when_brain_budget_is_off():
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=False))
    with pytest.raises(budget.RenderRefused):
        budget.render(WORKED_EXAMPLE_FULL, cfg)


def test_render_refuses_with_no_frontmatter():
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    with pytest.raises(budget.RenderRefused):
        budget.render("# just a heading\n", cfg)


def test_render_refuses_with_blockers_missing():
    text = WORKED_EXAMPLE_FULL.replace("## Blockers\n\n### B1", "## NotBlockers\n\n### B1")
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    with pytest.raises(budget.RenderRefused):
        budget.render(text, cfg)


def test_render_refuses_with_an_open_code_fence():
    text = WORKED_EXAMPLE_FULL.replace("## Summary\n\n", "## Summary\n\n```\n")
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    with pytest.raises(budget.RenderRefused):
        budget.render(text, cfg)


def test_render_refuses_with_an_invalid_ledger_schema():
    text = WORKED_EXAMPLE_FULL.replace("type: sequencing", "kind: sequencing")
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    with pytest.raises(budget.RenderRefused):
        budget.render(text, cfg)


def test_render_refuses_and_writes_nothing_reported_by_the_caller():
    # render() itself never writes; this documents that contract directly.
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=False))
    try:
        budget.render(WORKED_EXAMPLE_FULL, cfg)
        assert False, "should have refused"
    except budget.RenderRefused as e:
        assert e.reasons


def test_default_slug_lowercases_and_underscores():
    assert budget.default_slug("Add the CSV download!") == "add_the_csv_download"
    assert budget.default_slug("   ") == "design"


def test_scaffold_text_off_has_no_ledger_or_complexity_section():
    cfg = Config()
    text = budget.scaffold_text("A title", [], cfg, "2026-09-29")
    assert "brain_budget" not in text
    assert "## Complexity" not in text
    meta, _, err, _, _ = core.split_frontmatter(text)
    assert err is None and meta["type"] == "design"


def test_scaffold_text_on_has_ledger_and_empty_complexity_section():
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    text = budget.scaffold_text("A title", ["0007_x.md"], cfg, "2026-09-29")
    meta, _, err, _, _ = core.split_frontmatter(text)
    assert err is None
    assert meta["brain_budget"]["schema_version"] == budget.schema_version()
    assert meta["brain_budget"]["depends_on"] == [
        {"file": "0007_x.md", "contract": FORMAT_DEFINITION_MARKER}]
    assert "## Complexity\n\n## Blockers" in text


FORMAT_DEFINITION_MARKER = budget.FORMAT_DEFINITION["draft_marker"]


def test_in_budget_value_yes_no_and_na():
    cfg = Config(brain_budget=BrainBudgetConfig(enabled=True))
    doc = _load_as_doc(WORKED_EXAMPLE_FULL)
    assert budget.in_budget_value(doc, {doc.name: doc}, cfg) == "yes"

    over = _load_as_doc(WORKED_EXAMPLE_FULL.replace(
        "edges:\n    - from: Q1\n      to: Q2\n      type: sequencing",
        "edges:\n    - from: B1\n      to: Q1\n      type: coupled\n      contract: c\n"
        "    - from: Q1\n      to: Q2\n      type: coupled"))
    cfg_tight = Config(brain_budget=BrainBudgetConfig(
        enabled=True, limits=BudgetLimits(largest_coupled_cluster_size=2)))
    over2 = _load_as_doc(WORKED_EXAMPLE_FULL.replace(
        budget.policy_id(BudgetLimits()), budget.policy_id(BudgetLimits(largest_coupled_cluster_size=2))
    ).replace(
        "edges:\n    - from: Q1\n      to: Q2\n      type: sequencing\n      contract: Q2 orders "
        "the field set that Q1 selects. The order cannot change which fields Q1 selects.",
        "edges:\n    - from: B1\n      to: Q1\n      type: coupled\n      contract: c\n"
        "    - from: Q1\n      to: Q2\n      type: coupled\n      contract: c"))
    assert budget.in_budget_value(over2, {over2.name: over2}, cfg_tight) == "no"

    cfg_off = Config()
    assert budget.in_budget_value(doc, {doc.name: doc}, cfg_off) == "NA"

    note_text = WORKED_EXAMPLE_FULL.replace("type: design", "type: note").replace(
        "status: planning", "status: in-progress")
    note_doc = _load_as_doc(note_text)
    assert budget.in_budget_value(note_doc, {note_doc.name: note_doc}, cfg) == "NA"
