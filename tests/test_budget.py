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
