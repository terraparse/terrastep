"""Brain budget: the code-owned format definition and its two identity stamps
(0003, journal/plans/v0.2/0003_brain_budget_config_and_identity.md).

  terrastep design budget    prints whether brain budget is on, the effective
                              limits, and both identity stamps

0004 adds the declarations stage (the strict YAML loader, the schema
validator, the edge/graph/prerequisite rules, and the three structural
measures) and `terrastep design precheck`. 0005 adds the Complexity box,
`terrastep design render`/`scaffold`, and the layer inside `terrastep check`.

This module never writes a file.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

from .config import BudgetLimits

# The ledger schema (proposal section 5.4), without `properties.schema_version`
# — a schema cannot contain a hash of itself, so `working_schema()` below adds
# that property back once `schema_version()` is known. `required` still lists
# "schema_version": only the property was removed, not the requirement.
BASE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "policy_id", "depends_on", "edges"],
    "properties": {
        "policy_id": {"$ref": "#/$defs/identity"},
        "depends_on": {"type": "array", "items": {"$ref": "#/$defs/prerequisite"}},
        "edges": {"type": "array", "items": {"$ref": "#/$defs/edge"}},
    },
    "$defs": {
        "text": {"type": "string", "minLength": 1, "pattern": "\\S"},
        "identity": {"type": "string", "pattern": "^sha256:[0-9a-f]{12}$"},
        "document_file": {"type": "string", "pattern": "^[0-9]{4}_[^/\\\\]+\\.md$"},
        "element_id": {"type": "string", "pattern": "^[BQ][1-9][0-9]*$"},
        "prerequisite": {
            "type": "object",
            "additionalProperties": False,
            "required": ["file", "contract"],
            "properties": {
                "file": {"$ref": "#/$defs/document_file"},
                "contract": {"$ref": "#/$defs/text"},
            },
        },
        "edge": {
            "type": "object",
            "additionalProperties": False,
            "required": ["from", "to", "type", "contract"],
            "properties": {
                "from": {"$ref": "#/$defs/element_id"},
                "to": {"$ref": "#/$defs/element_id"},
                "type": {"enum": ["coupled", "sequencing"]},
                "contract": {"$ref": "#/$defs/text"},
            },
        },
    },
}

# The brain budget layer's whole format definition (proposal section 6.3):
# more than the schema, because a counting or wording change re-scores a
# document as surely as a schema change does. 0004 and 0005 implement the
# measure methods, the YAML profile and the Complexity box; this design
# defines all of their names up front, so `schema_version()` exists from the
# first commit and changes if either later design changes one.
FORMAT_DEFINITION = {
    "ledger_schema": BASE_SCHEMA,
    "complexity": {
        "heading": "Complexity",
        "placement": "last-front-section-before-blockers",
        "flag": {"true": "**Within budget: yes.**", "false": "**Within budget: no.**"},
        "columns": ["Measure", "Actual", "Limit"],
        "rows": [["evaluative_count", "Evaluative count"],
                 ["dependency_edge_count", "Dependency edge count"],
                 ["largest_coupled_cluster_size", "Largest coupled cluster size"],
                 ["word_count", "Word count"]],
    },
    "measure_methods": {
        "evaluative_count": "terrastep-bq-elements-v1",
        "dependency_edge_count": "edges-plus-depends-on-v1",
        "largest_coupled_cluster_size": "coupled-components-v1",
        "word_count": "whitespace-split-h1-to-sequencing-end-minus-complexity-v1",
    },
    "yaml_profile": "json-types-no-duplicates-no-aliases-v1",
    "draft_marker": "<!-- terrastep:draft -->",
}


def identity(value) -> str:
    """sha256: plus twelve hexadecimal characters of the value's canonical JSON
    (proposal section 6.4). Sorted keys and no insignificant whitespace, so
    reordering or reformatting terrastep.toml changes nothing."""
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def policy_id(limits: BudgetLimits) -> str:
    """The identity of the effective limits, after defaults are applied."""
    return identity(dataclasses.asdict(limits))


def schema_version() -> str:
    """The identity of the brain budget layer's format definition."""
    return identity(FORMAT_DEFINITION)


def working_schema() -> dict:
    """BASE_SCHEMA plus the current schema_version as a `const`, the schema a
    real ledger is validated against (0004)."""
    schema = json.loads(json.dumps(BASE_SCHEMA))  # a plain deep copy
    schema["properties"] = {**schema["properties"], "schema_version": {"const": schema_version()}}
    return schema
