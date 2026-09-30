# Complexity glossary: every term in the box, and how each is calculated

Written 2026-09-30. It is not a plan: it is outside `scan_dirs`, so it has no frontmatter and
terrastep does not check it. It exists so a reader of a plan's `## Complexity` section does not
have to open `src/terrastep/budget.py` to know what each word means.

The source of truth is the code, not this file: `src/terrastep/budget.py`, functions
`word_count`, `complexity_box`, `check_layer`, `largest_coupled_cluster`. If the two disagree,
the code is right and this file is stale — check `git log -- src/terrastep/budget.py` for what
changed.

## Where the box comes from

`## Complexity` is a front section that only `terrastep plan render` writes. A model never edits
it by hand. `terrastep check` recomputes every value in it from the plan's own body and ledger,
and fails `brain-budget-complexity` if what is on disk does not match what render would write.

Example, within budget:

```markdown
## Complexity

**Within budget: yes.**

| Measure | Actual | Limit |
| --- | ---: | ---: |
| Evaluative count | 3 | 10 |
| Dependency edge count | 2 | 11 |
| Largest coupled cluster size | 1 | 3 |
| Word count | 245 | 2000 |
```

Over budget, only the flag line changes:

```markdown
**Within budget: no.** Over: largest coupled cluster size 4 > 3 (B1, Q1, Q2, Q3).
```

## The four measures

### Evaluative count

**What it counts:** every blocker and question in the document — `B1`, `B2`, ... in `##
Blockers`, `Q1`, `Q2`, ... in `## Questions` — whether the tag is `[open]` or `[resolved]`.

**How it is calculated:** `core.decision_items(doc)` takes the *first* `## Blockers` section and
the *first* `## Questions` section, and keeps only items whose letter matches that section (a
`Q` item sitting inside `## Blockers` is a different rule's problem, `body-items`, not counted
here). The measure is `len(elements)`.

**Default limit:** 10.

**When it is known:** always — this measure never needs the ledger, so it is computed at both
the precheck (`declarations`) stage and the final (`terrastep check`) stage.

### Dependency edge count

**What it counts:** how many relationships this plan has declared — inside itself, and to other
plans.

**How it is calculated:** `len(ledger["edges"]) + len(ledger["depends_on"])` — the count of
`edges` entries plus the count of `depends_on` entries in the plan's own `brain_budget` ledger.
It is a flat sum: a plan is charged only for what it declares, never for plans that depend on
*it*.

**Default limit:** 11.

**When it is known:** only once the ledger has passed the strict YAML check, the format-identity
check, and the schema check (rules 2-4). If any of those fail, this measure is `null`, not `0` —
a broken ledger is not the same fact as an empty one.

### Largest coupled cluster size

**What it counts:** the size of the biggest group of evaluation elements that must be judged
together.

**How it is calculated** (`largest_coupled_cluster` in `budget.py`): build an undirected graph
with one node per evaluation element and one edge per declared relationship *of type `coupled`*
(edges of type `sequencing` are ignored here). The measure is the number of nodes in the largest
connected component. An element with no coupled edges is its own component, of size 1. A
document with no evaluation elements at all gives 0.

Only *valid* edges feed this graph — an edge whose `from`/`to` is not a real element ID in the
body, or a self-edge, is filtered out first and reported separately as `brain-budget-edge`; it
never reaches the cluster calculation.

**Default limit:** 3 — deliberately small. The working-memory research the proposal cites (3 to
5 chunks held at once) is about elements that must be judged *together*, which is exactly what a
coupled cluster is.

**When it is known:** same gate as dependency edge count — only after the ledger passes its
schema check.

### Word count

**What it counts:** the plan's own prose — not its frontmatter, not the Complexity box itself.

**How it is calculated** (`word_count` in `budget.py`): start at the H1 line (the line beginning
`# `). Walk every section in order; skip the `## Complexity` section entirely; stop counting
right after `## Sequencing` ends (so any dated section added later, like `## What was built
(2026-09-30)`, is excluded). Join the kept lines and split on whitespace; the measure is the
number of resulting tokens. Headings, code fences, and list markers all count as ordinary text.

**Default limit:** 2000.

**When it is known:** only at the `final` stage (a real `terrastep check`, or `terrastep plan
render`). The precheck (`terrastep plan precheck`) never computes it — it is listed under that
report's own `deferred_checks` — because word count is about finished prose, and precheck runs
*before* the model has written any.

## Within budget

**What it means:** every one of the four measures above is at or below its limit.

**How it is calculated:** collect whichever measures are not `null`. If all four are known,
`in_budget` is `True` only if every one of them is `<= its limit`; otherwise `False`. If even one
measure is still `null` (an unrendered or broken ledger, or — at the precheck stage — word count,
which is never computed there), `in_budget` is `null`, not a guess.

This is why a precheck's `"in_budget"` field is always `null`: word count is one of the four, and
precheck never has it. The precheck's own `"structural_in_budget"` is a *different*, narrower
flag — see below.

**What it does not do:** fail anything. `terrastep check` never rejects a document for being over
budget. It is a flag shown in the box, in `terrastep check --format json`, in the `STATUS.md` "In
budget" column, and as a `WARN:` line — never a `FAIL:` line.

## Terms the calculations depend on

**Evaluation element.** A blocker or a question — the thing `evaluative_count` counts. It is not
a field in the ledger; the ledger never repeats them. They exist exactly once, as headings or
bold run-ins in the plan's own `## Blockers`/`## Questions` sections.

**Edge.** A declared relationship between two evaluation elements *in the same plan*, recorded in
the ledger as `{from, to, type, contract}`. `type` is `coupled` or `sequencing` — nothing else is
valid.

- `coupled`: the two elements must be judged together; this is what feeds the cluster measure.
- `sequencing`: one element supplies a contract the other consumes, without reopening the
  supplier; this never enlarges a cluster.

**Coupled cluster.** A connected group of evaluation elements joined only by `coupled` edges.
`largest_coupled_cluster_size` is the size of the biggest one in the plan.

**Prerequisite (`depends_on`).** A different plan (by filename) that this one needs a stated
contract from. Counted once toward `dependency_edge_count`; never contributes to the cluster
measure, because a coupled cluster is always local to one plan's own elements.

**Ledger.** The `brain_budget:` mapping in a plan's frontmatter: two identity stamps
(`schema_version`, `policy_id`) plus `edges` and `depends_on`. `dependency_edge_count` and
`largest_coupled_cluster_size` both read directly from it; `evaluative_count` and `word_count` do
not — they read the body only.

**Structural measures.** `evaluative_count`, `dependency_edge_count`, and
`largest_coupled_cluster_size` — the three measures that do not need finished prose, so they are
the ones a precheck can report. `word_count` is deliberately left out of this group; it is the
fourth measure, not a structural one.

## Where each measure's limit lives

Every limit is a plain integer in `terrastep.toml`, under `[brain_budget.limits]`. There is no
limit for "Within budget" itself — it is derived, not configured. `terrastep plan budget` prints
the effective limits (defaults marked) plus both identity stamps; it never edits `terrastep.toml`.
