"""Brain budget: the code-owned format definition, its two identity stamps
(0003), and the declarations stage (0004,
journal/plans/v0.2/0004_brain_budget_declarations_and_precheck.md):
the strict YAML loader, the small schema validator, the edge/graph/
prerequisite rules, the three structural measures, and
`terrastep plan precheck`.

0005 adds the Complexity box, word_count, `plan render`/`scaffold`, and
the layer inside `terrastep check` (the "final" stage; `check_layer`'s
`stage` argument is prepared for it but only "declarations" is implemented
here).

This module never writes a file.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path

import yaml

from . import core
from .config import BudgetLimits, Config

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
# measure methods, the YAML profile and the Complexity box; this plan
# defines all of their names up front, so `schema_version()` exists from the
# first commit and changes if either later plan changes one.
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


# ------------------------------------------------------- the strict YAML loader
#
# yaml.safe_load resolves an alias, applies a merge key, and lets a duplicate
# key silently overwrite — it never raises for any of these (checked
# 2026-09-29). So there is no dict shape to inspect after construction; the
# only way to catch them is to walk the *composed node graph* before
# construction throws that information away (proposal 5.3, 11.4). This walk
# runs only on the `brain_budget` node, never on the rest of the frontmatter
# (Q4) — status_changed still needs yaml.safe_load's date conversion.

_ALLOWED_YAML_TAGS = frozenset({
    "tag:yaml.org,2002:str", "tag:yaml.org,2002:int", "tag:yaml.org,2002:float",
    "tag:yaml.org,2002:bool", "tag:yaml.org,2002:null",
    "tag:yaml.org,2002:seq", "tag:yaml.org,2002:map",
})
_MERGE_TAG = "tag:yaml.org,2002:merge"


def _strict_yaml_errors(node, seen: set[int], reasons: list[str]) -> None:
    """Append one reason per problem found while walking `node` (a
    yaml.compose() node): a node reached twice (an alias — PyYAML reuses the
    anchored node object), a merge key, a duplicate mapping key, or any tag
    outside the JSON-compatible core types."""
    if id(node) in seen:
        reasons.append(f"an alias or anchor reference (line {node.start_mark.line + 1})")
        return
    seen.add(id(node))

    if isinstance(node, yaml.MappingNode):
        if node.tag != "tag:yaml.org,2002:map":
            reasons.append(f"an unsupported tag {node.tag!r} (line {node.start_mark.line + 1})")
        seen_keys: set[str] = set()
        for key_node, value_node in node.value:
            if key_node.tag == _MERGE_TAG:
                reasons.append(f"a merge key (<<) (line {key_node.start_mark.line + 1})")
                continue
            if isinstance(key_node, yaml.ScalarNode):
                if key_node.value in seen_keys:
                    reasons.append(f"a duplicate key {key_node.value!r} "
                                   f"(line {key_node.start_mark.line + 1})")
                seen_keys.add(key_node.value)
            _strict_yaml_errors(key_node, seen, reasons)
            _strict_yaml_errors(value_node, seen, reasons)
    elif isinstance(node, yaml.SequenceNode):
        if node.tag != "tag:yaml.org,2002:seq":
            reasons.append(f"an unsupported tag {node.tag!r} (line {node.start_mark.line + 1})")
        for item in node.value:
            _strict_yaml_errors(item, seen, reasons)
    else:  # a ScalarNode: str, int, float, bool, null, or a disallowed tag
        if node.tag not in _ALLOWED_YAML_TAGS:
            reasons.append(f"an unsupported tag {node.tag!r} (line {node.start_mark.line + 1}); "
                           "for example an unquoted date is tagged 'timestamp'")


def _find_ledger_node(fm_text: str) -> "yaml.Node | None":
    """The composed node for the `brain_budget` key, or None if it is absent.
    Composing never fails on a duplicate key, an alias or a bad tag — those
    are all syntactically legal YAML; only _strict_yaml_errors rejects them."""
    root = yaml.compose(fm_text)
    if not isinstance(root, yaml.MappingNode):
        return None
    for key_node, value_node in root.value:
        if isinstance(key_node, yaml.ScalarNode) and key_node.value == "brain_budget":
            return value_node
    return None


@dataclasses.dataclass
class LedgerResult:
    # The already-parsed dict from doc.meta (core.split_frontmatter's ordinary
    # yaml.safe_load): once confirmed free of the constructs strict_errors
    # checks for, that dict is unambiguous, so there is no need to separately
    # re-construct it from the composed node.
    ledger: dict | None
    strict_errors: list[str]


def load_ledger(doc: core.Doc) -> LedgerResult:
    """Validate `doc`'s `brain_budget` value against the strict YAML profile.
    Assumes the caller already confirmed `doc.meta["brain_budget"]` is a dict
    (brain-budget-ledger-missing is a separate rule)."""
    raw = (doc.meta or {}).get("brain_budget")
    node = _find_ledger_node(doc.fm_text)
    if node is None:
        # Cannot happen when `raw` really is a dict: fm_text is the exact text
        # doc.meta was parsed from. Defensive, not a normal code path.
        return LedgerResult(None, ["brain_budget could not be located in the frontmatter"])
    reasons: list[str] = []
    _strict_yaml_errors(node, set(), reasons)
    return LedgerResult(None, reasons) if reasons else LedgerResult(raw, [])


# ------------------------------------------------------------ the schema validator
#
# Exactly the ten JSON Schema 2020-12 keywords the ledger schema uses (Q3):
# type, properties, required, additionalProperties: false, items, enum,
# const, pattern, minLength, and a local $ref into $defs. A keyword-guard
# test fails if BASE_SCHEMA ever uses another one; a conformance test checks
# this validator against the real `jsonschema` package (dev extra only).

_SUPPORTED_SCHEMA_KEYWORDS = frozenset({
    "$schema", "$defs", "$ref", "type", "properties", "required",
    "additionalProperties", "items", "enum", "const", "pattern", "minLength",
})


@dataclasses.dataclass
class SchemaError:
    path: str
    expected: str
    actual: object


def _resolve(schema: dict, root: dict) -> dict:
    if "$ref" in schema:
        name = schema["$ref"].removeprefix("#/$defs/")
        return root["$defs"][name]
    return schema


def _validate(value, schema: dict, root: dict, path: str, errors: list[SchemaError]) -> None:
    schema = _resolve(schema, root)

    if "const" in schema:
        if value != schema["const"]:
            errors.append(SchemaError(path, f"the exact value {schema['const']!r}", value))
        return
    if "enum" in schema:
        if value not in schema["enum"]:
            errors.append(SchemaError(path, f"one of {schema['enum']!r}", value))
        return

    kind = schema.get("type")
    if kind == "string":
        if not isinstance(value, str) or isinstance(value, bool):
            errors.append(SchemaError(path, "a string", value))
            return
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(SchemaError(path, f"at least {schema['minLength']} character(s)", value))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(SchemaError(path, f"a string matching {schema['pattern']!r}", value))
    elif kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(SchemaError(path, "an integer", value))
    elif kind == "array":
        if not isinstance(value, list):
            errors.append(SchemaError(path, "an array", value))
            return
        item_schema = schema.get("items")
        if item_schema is not None:
            for i, item in enumerate(value):
                _validate(item, item_schema, root, f"{path}[{i}]", errors)
    elif kind == "object":
        if not isinstance(value, dict):
            errors.append(SchemaError(path, "an object", value))
            return
        props: dict = schema.get("properties", {})
        for key in schema.get("required", ()):
            if key not in value:
                errors.append(SchemaError(f"{path}.{key}", "this key, but it is missing", None))
        if schema.get("additionalProperties") is False:
            for key in sorted(set(value) - set(props)):
                errors.append(SchemaError(f"{path}.{key}", "no such key", value[key]))
        for key, sub_schema in props.items():
            if key in value:
                _validate(value[key], sub_schema, root, f"{path}.{key}", errors)


def validate(value, schema: dict) -> list[SchemaError]:
    """Every way `value` fails `schema`, each with a path like
    'brain_budget.edges[1].type'."""
    errors: list[SchemaError] = []
    _validate(value, schema, schema, "brain_budget", errors)
    return errors


# --------------------------------------------------- clusters, cycles, the layer

def largest_coupled_cluster(element_ids: list[str], edges: list[dict]) -> tuple[int, list[str]]:
    """proposal section 4.5, unchanged: the node count of the largest
    connected component in the undirected graph of `coupled` edges. 0 with no
    elements, 1 for an isolated element. `edges` must reference only IDs in
    `element_ids` (the caller filters invalid edges out first — brain-budget-edge
    already reports those separately)."""
    neighbors = {element_id: set() for element_id in element_ids}
    for edge in edges:
        if edge.get("type") == "coupled":
            neighbors[edge["from"]].add(edge["to"])
            neighbors[edge["to"]].add(edge["from"])
    visited, largest, members = set(), 0, []
    for node in neighbors:
        if node in visited:
            continue
        stack, component = [node], []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(neighbors[current] - visited)
        if len(component) > largest:
            largest, members = len(component), sorted(component, key=_ident_key)
    return largest, members


def _ident_key(ident: str) -> tuple[str, int]:
    """Sort blockers before questions, then by number (the convention the
    proposal uses for a mutual coupled edge's declared direction, section 4.3)."""
    return (ident[0], int(ident[1:]))


def _coupled_cluster_of(element_ids: list[str], edges: list[dict]) -> dict[str, int]:
    """element_id -> an arbitrary but stable cluster index, via `coupled`
    edges only."""
    neighbors = {e: set() for e in element_ids}
    for edge in edges:
        if edge.get("type") == "coupled":
            neighbors[edge["from"]].add(edge["to"])
            neighbors[edge["to"]].add(edge["from"])
    cluster_of: dict[str, int] = {}
    next_cluster = 0
    for node in element_ids:
        if node in cluster_of:
            continue
        stack = [node]
        while stack:
            current = stack.pop()
            if current in cluster_of:
                continue
            cluster_of[current] = next_cluster
            stack.extend(neighbors[current] - set(cluster_of))
        next_cluster += 1
    return cluster_of


def _any_cycle(graph: dict) -> list | None:
    """Any directed cycle in `graph` ({node: {neighbor, ...}}), as the list of
    nodes on it, or None. Standard white/gray/black DFS; these graphs are a
    handful of nodes (one document's coupled clusters, or a repository's
    plans), so a plain recursive search is fine."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict = {}
    stack: list = []

    def visit(node):
        color[node] = GRAY
        stack.append(node)
        for nxt in graph.get(node, ()):
            state = color.get(nxt, WHITE)
            if state == GRAY:
                return list(stack[stack.index(nxt):]) + [nxt]
            if state == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    nodes = set(graph) | {n for targets in graph.values() for n in targets}
    for node in nodes:
        if color.get(node, WHITE) == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def _cycle_containing(graph: dict[str, set], start: str) -> list[str] | None:
    """A path start -> ... -> start in `graph`, or None. Used for the
    prerequisite cycle (rule 8b), which is evaluated per document against a
    graph shared by the whole corpus — a graph that may hold other, unrelated
    cycles the caller does not want reported on this file."""
    def dfs(node: str, path: list[str]) -> list[str] | None:
        for nxt in graph.get(node, ()):
            if nxt == start:
                return path + [nxt]
            if nxt in path:
                continue
            found = dfs(nxt, path + [nxt])
            if found:
                return found
        return None
    return dfs(start, [start])


def _check_edges(element_ids: set[str], edges: list) -> tuple[list[dict], list[core.Finding]]:
    """proposal 7.2 rule 6. Returns (valid_edges, failures) — valid_edges (both
    endpoints real, no self-edge) is what the cluster/cycle rules and the
    dependency_edge_count measure use; a malformed edge is reported here and
    excluded from those, so it cannot crash largest_coupled_cluster."""
    failures: list[core.Finding] = []
    valid: list[dict] = []
    seen_ordered: set[tuple[str, str]] = set()
    coupled_pairs: set[frozenset] = set()
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue  # brain-budget-schema already reports this
        frm, to, etype = edge.get("from"), edge.get("to"), edge.get("type")
        prefix = f"brain_budget.edges[{i}]"
        bad = False
        if frm not in element_ids:
            failures.append(core.Finding(
                "brain-budget-edge", f"{prefix}.from names {frm!r}, which is not an evaluation "
                "element in this document", path=f"{prefix}.from",
                expected="an evaluation element ID in Blockers or Questions", actual=frm))
            bad = True
        if to not in element_ids:
            failures.append(core.Finding(
                "brain-budget-edge", f"{prefix}.to names {to!r}, which is not an evaluation "
                "element in this document", path=f"{prefix}.to",
                expected="an evaluation element ID in Blockers or Questions", actual=to))
            bad = True
        if bad:
            continue
        if frm == to:
            failures.append(core.Finding("brain-budget-edge", f"{prefix} is a self-edge ({frm!r})",
                                          path=prefix, expected="from != to", actual=frm))
            continue
        ordered, unordered = (frm, to), frozenset((frm, to))
        if ordered in seen_ordered:
            failures.append(core.Finding(
                "brain-budget-edge", f"{prefix} repeats {frm} -> {to}, already declared",
                path=prefix, expected="one record per ordered pair", actual=f"{frm}->{to}"))
            continue
        if etype == "coupled" and unordered in coupled_pairs:
            failures.append(core.Finding(
                "brain-budget-edge",
                f"{prefix} is a reverse copy of the already-declared coupled pair {to}/{frm}",
                path=prefix, expected="one edge per unordered coupled pair", actual=f"{frm}->{to}"))
            continue
        if etype == "sequencing" and unordered in coupled_pairs:
            failures.append(core.Finding(
                "brain-budget-edge",
                f"{prefix} is a sequencing record for {frm}/{to}, which is already coupled",
                path=prefix, expected="no sequencing record for an already-coupled pair",
                actual=f"{frm}->{to}"))
            continue
        seen_ordered.add(ordered)
        if etype == "coupled":
            coupled_pairs.add(unordered)
        valid.append(edge)
    return valid, failures


def _check_sequencing_cycle(element_ids: list[str], edges: list[dict]) -> core.Finding | None:
    """proposal 7.2 rule 7: after coupled clusters collapse to one node each,
    the sequencing edges must have no cycle."""
    cluster_of = _coupled_cluster_of(element_ids, edges)
    graph: dict[int, set[int]] = {}
    for edge in edges:
        if edge.get("type") != "sequencing":
            continue
        a, b = cluster_of.get(edge["from"]), cluster_of.get(edge["to"])
        if a is None or b is None or a == b:
            continue
        graph.setdefault(a, set()).add(b)
    cycle_clusters = _any_cycle(graph)
    if cycle_clusters is None:
        return None
    members = sorted((e for e, c in cluster_of.items() if c in set(cycle_clusters)), key=_ident_key)
    return core.Finding("brain-budget-cycle",
                        f"sequencing edges form a cycle after coupled clusters collapse: {members}")


def _check_prereqs(doc_name: str, depends_on: list, corpus: dict[str, core.Doc]) -> list[core.Finding]:
    """proposal 7.2 rule 8 (the per-document half; the cross-document cycle
    is _prereq_cycle_finding below)."""
    failures: list[core.Finding] = []
    seen_files: set = set()
    for i, entry in enumerate(depends_on):
        if not isinstance(entry, dict):
            continue  # brain-budget-schema already reports this
        file = entry.get("file")
        prefix = f"brain_budget.depends_on[{i}].file"
        if file == doc_name:
            failures.append(core.Finding("brain-budget-prereq", f"{prefix} names this file",
                                          path=prefix, expected="another scanned plan document",
                                          actual=file))
        elif file in seen_files:
            failures.append(core.Finding(
                "brain-budget-prereq", f"{prefix} ({file!r}) repeats an earlier entry",
                path=prefix, expected="a file listed once", actual=file))
        elif file not in corpus or corpus[file].type != "plan":
            failures.append(core.Finding(
                "brain-budget-prereq", f"{prefix} ({file!r}) is not a scanned plan document",
                path=prefix, expected="a scanned plan document", actual=file))
        seen_files.add(file)
    return failures


def _prereq_graph(corpus: dict[str, core.Doc]) -> dict[str, set]:
    graph: dict[str, set] = {}
    for name, doc in corpus.items():
        if doc.type != "plan":
            continue
        raw = (doc.meta or {}).get("brain_budget")
        targets = raw.get("depends_on") if isinstance(raw, dict) else None
        if not isinstance(targets, list):
            continue
        graph[name] = {e["file"] for e in targets if isinstance(e, dict)
                       and isinstance(e.get("file"), str)}
    return graph


def _prereq_cycle_finding(doc_name: str, corpus: dict[str, core.Doc]) -> core.Finding | None:
    cycle = _cycle_containing(_prereq_graph(corpus), doc_name)
    if cycle is None:
        return None
    return core.Finding("brain-budget-prereq-cycle",
                        f"plans depend on each other in a cycle: {' -> '.join(cycle)}")


def _contains_draft_marker(value) -> bool:
    marker = FORMAT_DEFINITION["draft_marker"]
    if isinstance(value, str):
        return marker in value
    if isinstance(value, list):
        return any(_contains_draft_marker(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_draft_marker(v) for v in value.values())
    return False


_ALL_MEASURES = ("evaluative_count", "dependency_edge_count", "largest_coupled_cluster_size",
                "word_count")


def word_count(doc: core.Doc) -> int:
    """proposal 4.5: from the H1 line through the end of ## Sequencing, with
    the whole `## Complexity` section removed. Reassembled from doc.sections
    (each heading's original text plus its lines) rather than re-parsing raw
    text — this is a word count, so exact spacing does not matter, only which
    lines are in or out."""
    lines = doc.body.splitlines()
    h1_idx = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)
    counted: list[str] = [] if h1_idx is None else [lines[h1_idx]]
    for section in doc.sections:
        if section.kind == "F" and section.role == "complexity":
            continue
        counted.append(f"## {section.title}")
        counted.extend(section.lines)
        if section.kind == "S":
            break  # a dated section after Sequencing is never counted
    return len("\n".join(counted).split())


def complexity_box(measures: dict, limits: dict, cluster_members: list[str], in_budget: bool) -> str:
    """proposal 5.6, the exact text `terrastep plan render` writes and
    `terrastep check` compares against (brain-budget-complexity)."""
    rows = FORMAT_DEFINITION["complexity"]["rows"]
    lines = ["## Complexity", ""]
    if in_budget:
        lines.append(FORMAT_DEFINITION["complexity"]["flag"]["true"])
    else:
        over = []
        for machine, label in rows:
            if measures[machine] is not None and measures[machine] > limits[machine]:
                text = f"{label.lower()} {measures[machine]} > {limits[machine]}"
                if machine == "largest_coupled_cluster_size":
                    text += f" ({', '.join(cluster_members)})"
                over.append(text)
        lines.append(f"{FORMAT_DEFINITION['complexity']['flag']['false']} Over: "
                     + "; ".join(over) + ".")
    lines += ["", "| Measure | Actual | Limit |", "| --- | ---: | ---: |"]
    lines += [f"| {label} | {measures[machine]} | {limits[machine]} |" for machine, label in rows]
    return "\n".join(lines) + "\n"


def _check_complexity_box(doc: core.Doc, expected_box: str) -> core.Finding | None:
    """rule 10 (final only): the box is present, is the last front section,
    sits just before ## Blockers, and equals what render would write."""
    complexity_secs = [(i, s) for i, s in enumerate(doc.sections)
                       if s.kind == "F" and s.role == "complexity"]
    blocker_secs = [(i, s) for i, s in enumerate(doc.sections) if s.kind == "B"]
    if not complexity_secs:
        return core.Finding("brain-budget-complexity", "the Complexity box is missing; "
                            "run `terrastep plan render`")
    if len(complexity_secs) > 1:
        return core.Finding("brain-budget-complexity", "more than one Complexity section; "
                            "run `terrastep plan render`")
    idx, section = complexity_secs[0]
    if not blocker_secs or idx != blocker_secs[0][0] - 1:
        return core.Finding("brain-budget-complexity",
                            "the Complexity box is not the last front section, just before "
                            "## Blockers; run `terrastep plan render`")
    actual = f"## {section.title}\n" + "\n".join(section.lines)
    # A whitespace-only difference is not a rewrite the model could have made
    # by hand; compare the meaningful content, not every trailing blank line.
    if actual.strip() != expected_box.strip():
        return core.Finding("brain-budget-complexity",
                            "the Complexity box does not match what `terrastep plan render` "
                            "would write; run it again")
    return None


@dataclasses.dataclass
class LayerResult:
    failures: list[core.Finding]
    warnings: list[str]
    measures: dict[str, "int | None"]
    cluster_members: list[str]
    in_budget: "bool | None" = None


def check_layer(doc: core.Doc, corpus: dict[str, core.Doc], cfg: Config, stage: str) -> LayerResult:
    """The brain budget layer's own rules (proposal 7.2), rules 1-10.
    `corpus` maps every scanned filename (Doc.name, a bare basename — safe
    because fm-id-dup already requires unique numbers repository-wide) to
    its Doc. `stage` is "declarations" (0004: terrastep plan precheck) or
    "final" (0005: terrastep check) — both run rules 1-9 identically; "final"
    also computes word_count and runs rule 10 (the Complexity box)."""
    assert stage in ("declarations", "final")
    failures: list[core.Finding] = []
    warnings: list[str] = []
    elements = core.decision_items(doc)
    element_ids = {i.ident for i in elements}
    measures: dict[str, "int | None"] = {
        "evaluative_count": len(elements),
        "dependency_edge_count": None,
        "largest_coupled_cluster_size": None,
        "word_count": word_count(doc) if stage == "final" else None,
    }
    cluster_members: list[str] = []
    limits = dataclasses.asdict(cfg.brain_budget.limits)

    def finish(schema_valid: bool) -> LayerResult:
        # Rule 10 (final only, and only with a valid ledger shape — the box
        # cannot be honestly compared without real edge/prereq measures).
        if stage == "final" and schema_valid:
            in_budget_now = all(measures[m] is not None and measures[m] <= limits[m]
                                for m in _ALL_MEASURES)
            box = complexity_box(measures, limits, cluster_members, in_budget_now)
            box_finding = _check_complexity_box(doc, box)
            if box_finding:
                failures.append(box_finding)
        known = {m: v for m, v in measures.items() if v is not None}
        in_budget = all(known[m] <= limits[m] for m in known) if len(known) == len(_ALL_MEASURES) \
            else None
        for m in _ALL_MEASURES:
            if measures[m] is not None and measures[m] > limits[m]:
                warnings.append(_over_budget_warning(m, measures[m], limits[m], cluster_members))
        return LayerResult(failures, warnings, measures, cluster_members, in_budget)

    # Rule 1: ledger present.
    raw = (doc.meta or {}).get("brain_budget")
    if not isinstance(raw, dict):
        failures.append(core.Finding("brain-budget-ledger-missing",
                                     "brain_budget is missing or is not a mapping"))
        return finish(schema_valid=False)

    # Rule 2: strict YAML. Stop on failure.
    loaded = load_ledger(doc)
    if loaded.strict_errors:
        failures.append(core.Finding(
            "brain-budget-yaml-strict",
            "brain_budget has " + "; ".join(loaded.strict_errors)))
        return finish(schema_valid=False)
    ledger = loaded.ledger

    # Rule 3: format identity. Stop on failure.
    current_schema_version = schema_version()
    if ledger.get("schema_version") != current_schema_version:
        failures.append(core.Finding(
            "brain-budget-schema-version",
            f"schema_version is {ledger.get('schema_version')!r}, expected "
            f"{current_schema_version!r}; run `terrastep plan render`",
            path="brain_budget.schema_version", expected=current_schema_version,
            actual=ledger.get("schema_version")))
        return finish(schema_valid=False)

    # Rule 4: schema.
    schema_errors = validate(ledger, working_schema())
    for err in schema_errors:
        failures.append(core.Finding("brain-budget-schema",
                                     f"{err.path}: expected {err.expected}, got {err.actual!r}",
                                     path=err.path, expected=err.expected, actual=err.actual))

    # Rule 5: policy identity. Runs regardless of the schema result (a simple
    # string compare), unlike rules 6-8 below.
    current_policy_id = policy_id(cfg.brain_budget.limits)
    if ledger.get("policy_id") != current_policy_id:
        failures.append(core.Finding(
            "brain-budget-policy-id",
            f"policy_id is {ledger.get('policy_id')!r}, expected {current_policy_id!r}; "
            "run `terrastep plan render`, then check again",
            path="brain_budget.policy_id", expected=current_policy_id, actual=ledger.get("policy_id")))

    if schema_errors:
        # The ledger's shape cannot be trusted for edges, cycles, prereqs, or
        # the two ledger-dependent measures.
        return finish(schema_valid=False)

    edges = ledger.get("edges", [])
    depends_on = ledger.get("depends_on", [])
    measures["dependency_edge_count"] = len(edges) + len(depends_on)

    # Rule 6: edges.
    valid_edges, edge_failures = _check_edges(element_ids, edges)
    failures.extend(edge_failures)

    cluster_size, cluster_members = largest_coupled_cluster(
        sorted(element_ids, key=_ident_key), valid_edges)
    measures["largest_coupled_cluster_size"] = cluster_size

    # Rule 7: sequencing cycle.
    cycle_finding = _check_sequencing_cycle(sorted(element_ids, key=_ident_key), valid_edges)
    if cycle_finding:
        failures.append(cycle_finding)

    # Rule 8: prerequisites (per document, then the cross-document cycle).
    failures.extend(_check_prereqs(doc.name, depends_on, corpus))
    prereq_cycle = _prereq_cycle_finding(doc.name, corpus)
    if prereq_cycle:
        failures.append(prereq_cycle)

    # Rule 9: draft markers. "final" scans the whole file; "declarations"
    # scans only the ledger, Blockers, and Questions.
    marker = FORMAT_DEFINITION["draft_marker"]
    if stage == "final":
        marker_present = marker in doc.body or _contains_draft_marker(ledger)
    else:
        in_body = any(marker in "\n".join(sec.lines) for sec in doc.sections if sec.kind in ("B", "Q"))
        marker_present = _contains_draft_marker(ledger) or in_body
    if marker_present:
        scope = "the file" if stage == "final" else "the ledger, Blockers, or Questions"
        failures.append(core.Finding(
            "brain-budget-draft-marker", f"a scaffold draft marker ({marker}) is still present in "
                                        f"{scope}"))

    return finish(schema_valid=True)


# --------------------------------------------------------------- the precheck report

DEFERRED_CHECKS = ("front_sections", "recommendations_coverage", "sequencing", "word_count",
                   "complexity_box", "draft_markers_outside_elements")
_STRUCTURAL_MEASURES = ("evaluative_count", "dependency_edge_count", "largest_coupled_cluster_size")
_MEASURE_LABELS = dict(FORMAT_DEFINITION["complexity"]["rows"])
PRECHECK_BODY_CODES = frozenset({"body-order", "body-items", "body-tag", "body-recommend", "body-empty"})


def _finding_dict(f: core.Finding) -> dict:
    return {"code": f.code, "message": f.message, "path": f.path,
            "expected": f.expected, "actual": f.actual}


def _over_budget_warning(measure: str, actual: int, limit: int, members: list[str]) -> str:
    text = f"over budget: {_MEASURE_LABELS[measure].lower()} {actual} > {limit}"
    if measure == "largest_coupled_cluster_size":
        text += f" ({', '.join(members)})"
    return text


def precheck_report(doc: core.Doc, corpus: dict[str, core.Doc], cfg: Config,
                    extra_failures: list[core.Finding]) -> dict:
    """The full `terrastep plan precheck` report (proposal 7.8): frontmatter
    and the filtered body findings (`extra_failures`, gathered by the caller)
    plus this plan's own layer rules, at the declarations stage."""
    layer = check_layer(doc, corpus, cfg, stage="declarations")
    failures = list(extra_failures) + layer.failures
    measures = layer.measures
    limits = dataclasses.asdict(cfg.brain_budget.limits)

    if any(measures[m] is None for m in _STRUCTURAL_MEASURES):
        structural_in_budget = None
        over_budget: list[dict] = []
    else:
        over_budget = []
        for m in _STRUCTURAL_MEASURES:
            if measures[m] > limits[m]:
                entry = {"measure": m, "actual": measures[m], "limit": limits[m]}
                if m == "largest_coupled_cluster_size":
                    entry["members"] = layer.cluster_members
                over_budget.append(entry)
        structural_in_budget = not over_budget

    return {
        "file": doc.rel,
        "stage": "declarations",
        "declarations_valid": not failures,
        "structural_in_budget": structural_in_budget,
        "format_valid": None,
        "in_budget": None,
        "policy_id": policy_id(cfg.brain_budget.limits),
        "schema_version": schema_version(),
        "measures": measures,
        "limits": limits,
        "over_budget": over_budget,
        "deferred_checks": list(DEFERRED_CHECKS),
        "failures": [_finding_dict(f) for f in failures],
        "warnings": [_over_budget_warning(e["measure"], e["actual"], e["limit"], layer.cluster_members)
                    for e in over_budget],
    }


# --------------------------------------------------------------------- render

class RenderRefused(Exception):
    """`terrastep plan render` writes nothing; `reasons` names why."""
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def _render_check_schema() -> dict:
    """working_schema(), except schema_version only needs the identity SHAPE,
    not today's exact hash — render's whole job is to fix a stale one (9.5,
    "stamp values are ignored for this test")."""
    schema = json.loads(json.dumps(BASE_SCHEMA))
    schema["properties"] = {**schema["properties"], "schema_version": {"$ref": "#/$defs/identity"}}
    return schema


def _has_unterminated_fence(body: str) -> bool:
    in_fence = False
    for ln in body.splitlines():
        if core.FENCE_RE.match(ln):
            in_fence = not in_fence
    return in_fence


def _rewrite_stamps_in_place(text: str, fm_text: str, fm_offset: int,
                              new_schema_version: str, new_policy_id: str) -> str:
    """Replace schema_version's and policy_id's values at the exact character
    spans yaml.compose() marks on the parsed nodes, translated into the whole
    file's coordinates via fm_offset. Every other byte — sibling keys,
    comments, quoting — is untouched (9.5, point 2)."""
    root = yaml.compose(fm_text)
    bb_node = next(v for k, v in root.value if isinstance(k, yaml.ScalarNode)
                  and k.value == "brain_budget")
    replacements: list[tuple[int, int, str]] = []
    for key_node, value_node in bb_node.value:
        if key_node.value == "schema_version":
            replacements.append((value_node.start_mark.index, value_node.end_mark.index,
                                 new_schema_version))
        elif key_node.value == "policy_id":
            replacements.append((value_node.start_mark.index, value_node.end_mark.index,
                                 new_policy_id))
    result = text
    for start, end, new_value in sorted(replacements, key=lambda r: r[0], reverse=True):
        abs_start, abs_end = fm_offset + start, fm_offset + end
        result = result[:abs_start] + new_value + result[abs_end:]
    return result


def _append_ledger(text: str, fm_end_offset: int, new_schema_version: str,
                    new_policy_id: str) -> str:
    """Add brain_budget as the frontmatter's last key, right before the
    closing '---' — the safe way to add a new top-level YAML key without
    re-serializing (and so disturbing) any existing one (9.5, point 3)."""
    ledger_yaml = (f"brain_budget:\n  schema_version: {new_schema_version}\n"
                  f"  policy_id: {new_policy_id}\n  depends_on: []\n  edges: []\n")
    prefix = text[:fm_end_offset]
    if not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + ledger_yaml + text[fm_end_offset:]


def _upsert_complexity_box(body: str, box: str, aliases: dict) -> str:
    """Replace an existing Complexity section's lines with `box`, or insert
    `box` just before ## Blockers if there is none yet (9.5, point 4)."""
    role_patterns = core.build_role_patterns(aliases)
    lines = body.split("\n")
    in_fence = False
    heading_at: list[tuple[int, str, str | None]] = []  # (line, kind, role)
    for i, ln in enumerate(lines):
        if core.FENCE_RE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = core.HEADING2_RE.match(ln)
        if m:
            kind, role = core.classify(m.group(1), role_patterns)
            heading_at.append((i, kind, role))

    blockers_at = next((i for i, kind, _ in heading_at if kind == "B"), len(lines))
    complexity_idx = next((n for n, (i, kind, role) in enumerate(heading_at)
                          if kind == "F" and role == "complexity"), None)
    box_lines = box.rstrip("\n").split("\n")

    if complexity_idx is not None:
        start = heading_at[complexity_idx][0]
        end = (heading_at[complexity_idx + 1][0] if complexity_idx + 1 < len(heading_at)
              else blockers_at)
        new_lines = lines[:start] + box_lines + [""] + lines[end:]
    else:
        new_lines = lines[:blockers_at] + box_lines + [""] + lines[blockers_at:]
    return "\n".join(new_lines)


def render(text: str, cfg: Config) -> str:
    """`budget.render(text, cfg) -> new text`, or raises RenderRefused
    (proposal 9.5). Idempotent: a second call on its own output returns
    the same text unchanged."""
    if not cfg.brain_budget.enabled:
        raise RenderRefused(["brain budget is not enabled"])
    meta, body, yaml_error, fm_text, fm_offset = core.split_frontmatter(text)
    if meta is None:
        raise RenderRefused(["no frontmatter block"])
    if yaml_error:
        raise RenderRefused([f"frontmatter does not parse: {yaml_error}"])
    if _has_unterminated_fence(body):
        raise RenderRefused(["a code fence is left open"])
    role_patterns = core.build_role_patterns(cfg.aliases)
    sections = core.parse_sections(body, role_patterns)
    if not any(s.kind == "B" for s in sections):
        raise RenderRefused(["## Blockers is missing"])

    raw_ledger = meta.get("brain_budget")
    ledger_present = isinstance(raw_ledger, dict)
    if ledger_present:
        probe = core.Doc(path=Path("<render>"), rel="<render>", meta=meta, yaml_error=None,
                         body=body, sections=sections, fm_text=fm_text, fm_offset=fm_offset)
        strict = load_ledger(probe)
        if strict.strict_errors:
            raise RenderRefused(["brain_budget has " + "; ".join(strict.strict_errors)])
        schema_errors = validate(raw_ledger, _render_check_schema())
        if schema_errors:
            raise RenderRefused([f"{e.path}: expected {e.expected}, got {e.actual!r}"
                                for e in schema_errors])

    new_sv, new_pid = schema_version(), policy_id(cfg.brain_budget.limits)
    if ledger_present:
        new_text = _rewrite_stamps_in_place(text, fm_text, fm_offset, new_sv, new_pid)
    else:
        new_text = _append_ledger(text, fm_offset + len(fm_text), new_sv, new_pid)

    # Recompute against the new text, so the box reflects the stamps just
    # written (not the ones that may have just been replaced/added).
    new_meta, new_body, _, new_fm_text, new_fm_offset = core.split_frontmatter(new_text)
    new_sections = core.parse_sections(new_body, role_patterns)
    new_doc = core.Doc(path=Path("<render>"), rel="<render>", meta=new_meta, yaml_error=None,
                      body=new_body, sections=new_sections, fm_text=new_fm_text,
                      fm_offset=new_fm_offset)
    layer = check_layer(new_doc, {new_doc.name: new_doc}, cfg, stage="final")
    limits = dataclasses.asdict(cfg.brain_budget.limits)
    box = complexity_box(layer.measures, limits, layer.cluster_members, bool(layer.in_budget))
    frontmatter_prefix = new_text[:len(new_text) - len(new_body)]
    return frontmatter_prefix + _upsert_complexity_box(new_body, box, cfg.aliases)


# ------------------------------------------------------------------- scaffold

def scaffold_text(title: str, depends_on: list[str], cfg: Config, today: str) -> str:
    """The new file's content for `terrastep plan scaffold` (proposal 5.7,
    9.3). `today` is status_changed's value (an ISO date string), passed in
    rather than read from the clock here, so a test can pin it. With brain
    budget off: a plain skeleton, no ledger, no Complexity section (9.3,
    point 6) — useful to every terrastep repository, not just budgeted ones."""
    meta: dict = {
        "status": "planning",
        "status_changed": today,
        "type": "plan",
        "next": "Owner reviews.",
    }
    if cfg.brain_budget.enabled:
        marker = FORMAT_DEFINITION["draft_marker"]
        meta["brain_budget"] = {
            "schema_version": schema_version(),
            "policy_id": policy_id(cfg.brain_budget.limits),
            "depends_on": [{"file": f, "contract": marker} for f in depends_on],
            "edges": [],
        }
    frontmatter = yaml.dump(meta, sort_keys=False, default_flow_style=False)

    marker = FORMAT_DEFINITION["draft_marker"]
    body = [f"# {title}", "", "## Summary", marker, "", "## Scope", marker, "",
            "## The design", marker, "", "## Verification", marker, ""]
    if cfg.brain_budget.enabled:
        body += ["## Complexity", ""]
    body += ["## Blockers", marker, "", "## Questions", marker, "",
            "## Recommendations", marker, "", "## Sequencing", marker, ""]
    return f"---\n{frontmatter}---\n" + "\n".join(body)


def default_slug(title: str) -> str:
    """lower case, with other characters turned into `_` (9.3, point 2)."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug or "plan"


def in_budget_value(doc: core.Doc, corpus: dict[str, core.Doc], cfg: Config) -> str:
    """"yes", "no", or "NA" for the STATUS.md index column (5.9). Computed
    from freshly recomputed measures, not from the box last rendered."""
    if (not cfg.brain_budget.enabled or doc.type != "plan"
            or doc.status not in ("planning", "ready") or not (doc.meta and not doc.yaml_error)):
        return "NA"
    layer = check_layer(doc, corpus, cfg, stage="final")
    if layer.in_budget is None:
        return "NA"
    return "yes" if layer.in_budget else "no"


# ---------------------------------------------------------- the check report

_DEPENDENCY_CODES = frozenset({"brain-budget-edge", "brain-budget-cycle", "brain-budget-prereq",
                              "brain-budget-prereq-cycle"})


def check_report(docs: list[core.Doc], cfg: Config, failures: dict[str, list[core.Finding]],
                 warnings: dict[str, list[str]], only: set[str] | None, config_file: Path,
                 terrastep_version: str) -> dict:
    """`terrastep check --format json` (proposal 7.8). `failures`/`warnings`
    are core.check_corpus(...)'s result — this only reshapes them and adds
    each budgeted plan's brain_budget block."""
    corpus = {d.name: d for d in docs}
    index_rel = cfg.index_rel_path
    config_sha256 = (hashlib.sha256(config_file.read_bytes()).hexdigest()
                     if config_file.exists() else None)

    scanned = [d for d in docs if only is None or d.rel in only]
    doc_reports = []
    for d in scanned:
        entry = {
            "file": d.rel, "type": d.type, "status": d.status,
            "failures": [_finding_dict(f) for f in failures.get(d.rel, [])],
            "warnings": list(warnings.get(d.rel, [])),
        }
        if cfg.brain_budget.enabled and d.type == "plan" and d.status in ("planning", "ready"):
            layer = check_layer(d, corpus, cfg, stage="final")
            limits = dataclasses.asdict(cfg.brain_budget.limits)
            layer_codes = {f.code for f in layer.failures}
            open_blockers = [i.ident for i in core.decision_items(d) if i.letter == "B"
                            and "open" in core.TAG_RE.findall(i.first_line)]
            over_budget = []
            for m in _ALL_MEASURES:
                if layer.measures[m] is not None and layer.measures[m] > limits[m]:
                    e = {"measure": m, "actual": layer.measures[m], "limit": limits[m]}
                    if m == "largest_coupled_cluster_size":
                        e["members"] = layer.cluster_members
                    over_budget.append(e)
            entry["brain_budget"] = {
                "stage": "final",
                "format_valid": not bool(layer_codes),
                "in_budget": layer.in_budget,
                "over_budget": over_budget,
                "open_blockers": open_blockers,
                "dependency_validation": "failed" if layer_codes & _DEPENDENCY_CODES else "passed",
                "policy_id": policy_id(cfg.brain_budget.limits),
                "schema_version": schema_version(),
                "measures": layer.measures,
                "limits": limits,
                "file_sha256": (hashlib.sha256(d.path.read_bytes()).hexdigest()
                               if d.path.exists() else None),
            }
        doc_reports.append(entry)

    total_failures = sum(len(v) for v in failures.values())
    total_warnings = sum(len(v) for v in warnings.values())
    return {
        "terrastep_version": terrastep_version,
        "config_file": str(config_file),
        "config_sha256": config_sha256,
        "ok": total_failures == 0,
        "summary": {"documents": len(scanned), "failures": total_failures, "warnings": total_warnings},
        "documents": doc_reports,
        "corpus": {
            "failures": [_finding_dict(f) for f in failures.get(index_rel, [])],
            "warnings": list(warnings.get("(all)", [])),
        },
    }
