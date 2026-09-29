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

from terrastep import budget
from terrastep.config import BudgetLimits

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
