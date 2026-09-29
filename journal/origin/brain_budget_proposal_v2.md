# Brain budget for terrastep design documents (proposal v2)

**Proposal, version 2.** This version replaces [brain_budget_proposal.md](brain_budget_proposal.md)
(v1). It is self-contained: you do not need v1 or the research notes. Appendix A lists what changed
from v1 and from research note 4.2, and why.

This is not a terrastep document, so it has no frontmatter. In terrastep, it belongs in
`journal/origin/`, next to `handoff.md`, as the source for the terrastep design documents in
section 17.

**Status.** Proposal only. No code exists yet. Every command, module, field, failure code and file name
below is a proposal. Where this proposal says a value was computed or checked, it was: the ledger
schema was validated with the `jsonschema` library, and the worked example (section 5.8) passes
terrastep 0.1.0's real `terrastep check`.

**Readers.** The terrastep maintainer, who decides. The agent that turns this proposal into terrastep
design documents and then implements them.

## Contents

1. Summary
2. Why: the problem and the rationale
3. Concepts
4. The four measures
5. The document format
6. Identity: generated `policy_id` and `schema_version`
7. Validation
8. Configuration: `[brain_budget]` in `terrastep.toml`
9. CLI verbs
10. How an LLM writes design documents, step by step
11. Architecture in terrastep
12. Integration decisions
13. Open questions for the owner
14. Verification plan
15. Evaluation plan
16. What this proposal does not do
17. Suggested decomposition into terrastep design documents
- Appendix A: Changes from v1 and from research note 4.2
- Appendix B: References

---

## 1. Summary

An agent can write a design document faster than a person can review it well. A short feature request
often becomes one large document with many interacting choices. Brain budget measures how much
judgment one design document asks of its reviewer. It asks the agent to split the work into several
smaller designs when it can, and it reports honestly when it could not.

Brain budget is a **layer on terrastep's existing `type: design` documents**. terrastep's format stays
as it is: frontmatter, front sections, and Blockers, Questions, Recommendations, Sequencing. Brain
budget adds five things:

1. **A small ledger in the frontmatter**, under `brain_budget`: two generated identity stamps, the
   dependency edges between the document's evaluation elements, and the other design documents it depends on.
2. **Four measures**, computed by terrastep, each compared with a limit from a new `[brain_budget]`
   table in `terrastep.toml`: `evaluative_count`, `dependency_edge_count`,
   `largest_coupled_cluster_size`, and `word_count`.
3. **A Complexity box**: a new front section, placed just before `## Blockers`, that terrastep writes.
   It shows the four measures against their limits, and one flag: **Within budget: yes** or **no**.
   Being over budget is a flag, not a failure.
4. **Four staged CLI actions** so the agent can find problems before it writes prose:
   `terrastep design budget`, `terrastep design scaffold`, `terrastep design precheck`, and
   `terrastep design render`. The final validation is the existing `terrastep check`. It gets the new
   rules and a `--format json` option.
5. **An authoring procedure**, added to terrastep's generated Claude Code skill: decompose, order by
   prerequisite, scaffold, declare the evaluation elements, precheck, write, render, check, and retry at most
   `max_retries` times.

Notes and legacy documents are not budgeted. A repository opts in with
`[brain_budget] enabled = true`. With the default (`false`), terrastep checks documents exactly as it
does today. The one visible change is a permanent `In budget` column in `STATUS.md`, which then reads
`NA` for every document (section 5.9).

---

## 2. Why: the problem and the rationale

### 2.1 Review attention is the scarce resource

An agent can generate candidate work faster than a person can oversee it with care. Research on agentic
development describes this as work moving downstream, into verification and judgment. It proposes
*bounded delegation*: decide explicitly where the agent has authority and where human judgment is
required (Appendix B, [1], [8], [9]).

Brain budget applies this to design review. It bounds agent autonomy by **how much consequential
judgment a person can give well at the next approval point**, not by how much work the agent can do.

### 2.2 Count what the reviewer must judge, not words

Cognitive load theory defines complexity by *element interactivity*: how many elements a person must
process at the same time (Appendix B, [2], [4]). Ten independent facts are easy. Four architectural
choices that constrain each other are hard, even in fewer words. Working-memory research puts the
number of chunks a person can hold at once nearer 3 to 5 than 7 (Appendix B, [3]).

Compare two designs:

- "Feature A adds a CLI flag, three functions and four tests."
- "Feature A must choose Postgres or Redis for its state. That choice affects the retry model, the API
  idempotency contract, the migration, and the job executor."

The second one can be shorter. Its choices constrain each other much more. So brain budget counts the
evaluation elements the reviewer must judge, and how those evaluation elements are coupled. Word count is a secondary measure.

### 2.3 The model declares; code counts

An LLM must not score its own document. The model writes the evaluation elements and declares the edges between
them. Deterministic code counts them and computes the graph measures.

Code cannot prove that the declarations are complete. A model can leave out an evaluation element, and no count
notices. Brain budget makes every declared evaluation element visible and reviewable. It does not make an omission
impossible (section 4.6).

### 2.4 Change the shape of the work, not its verbosity

"Be concise" makes a model delete information that the reviewer needs. Brain budget says: **keep the
complexity, but split it into designs that can each be reviewed on their own.**

- Evaluation elements that constrain each other stay in one design (a *coupled cluster*).
- A split is allowed only where one design can rely on a stated contract from another.
- After a design is approved, its answers become fixed contracts for the designs that depend on it.
  A later design then has fewer evaluation elements to judge: it treats the earlier result as one known fact.

This follows established practice: progressive disclosure (Appendix B, [6]), small self-contained
reviews (Appendix B, [5]), and one decision per architecture decision record (Appendix B, [7]).

### 2.5 Separate limits, not one score

An early version proposed a weighted Review Complexity Index. It was dropped. Its weights were never
validated, and a single low total can hide one oversized cluster. Separate measures say exactly what
is over: "the coupled cluster B1, Q1, Q2, Q3 has 4 members; the limit is 3."

### 2.6 Budget each document, not the whole response

Earlier versions limited the number of plans in a response and the total words. Both limits were
removed. A reviewer reviews one document at a time. A response-wide limit pushes the model to drop
required scope so the response fits. So there is no limit on the number of designs, and each design
has its own budget. More files do not fix coupling: coupled evaluation elements stay in one design.

### 2.7 Find problems before prose

A check that runs only on the finished document wastes output. The model writes full prose for a
decomposition, and then a structural measure turns out to be over its limit. So the work has stages. A
tool writes the skeleton. The model writes the evaluation elements (a title and a recommendation each) and declares
the edges. A precheck measures them. Only then does the model write the prose. A tool renders the
Complexity box, the final check runs, and fixes patch only what was reported.

### 2.8 A flag, not a gate

v1 treated an over-budget document as an escalation (`needs_design`), with its own outcome, gate and
follow-up document. v2 drops all of that. The owner's hypothesis:

> The friction of an occasional design document that is harder than the standard costs the reviewer
> less than the friction of running an escalation process.

So:

- `max_retries` bounds how many tokens the agent spends trying to fit the budget.
- If the agent cannot fit within its retries, it delivers the document anyway, and the Complexity box
  says **Within budget: no**, and names the measures that are over.
- The reviewer knows, before reading, that this document is one of the harder ones.

This is also the right behavior for irreducible coupling. Coupled evaluation elements must stay together, so a
design with a large coupled cluster is flagged and reviewed as one unit. It is not split artificially.
Section 15 tests the hypothesis.

### 2.9 Limits for software developers

The defaults are calibrated for developers, who are used to reasoning about dependencies. They are not
calibrated for the median reader.

| Measure | Default | Reason |
|---|---:|---|
| `largest_coupled_cluster_size` | 3 | The working-memory figure (3 to 5 chunks) is about what a person must hold at once. Coupled evaluation elements must be held at once. This limit stays small. |
| `evaluative_count` | 10 | Evaluation elements that do not interact can be judged one after another. The total can be much higher than what is held at once. |
| `dependency_edge_count` | 11 | Enough for 10 evaluation elements with a few prerequisite contracts. |
| `word_count` | 2000 | The counted region is the whole terrastep design body: front sections plus Blockers, Questions, Recommendations and Sequencing. |

With 10 evaluation elements and a cluster limit of 3, the cluster limit is a real, separate check. (In v1, with a
decision limit of 3, it never added anything.) All defaults are experiments. A repository tunes them
from evidence (section 15). Each set of limits has its own generated `policy_id`, so records from
different policies do not get mixed.

### 2.10 How the design got here

| Stage | What it added | What later changed, and why |
|---|---|---|
| Research note 1 | Review attention as the constraint. Decisions and coupling as the measure. Decompose into review packets. | The weighted score was dropped. |
| Note 2 | Observations versus declarations. A graph with `coupled` and `sequencing` edges. Cluster size from connected components. | Repository-derived measures and diff-size budgets were deferred. |
| Note 3 | A small contract: one policy, one format, one checker. | — |
| Note 4 | Full measure names. One configuration file. YAML frontmatter under one namespace. | — |
| Note 4.1 | One plan per file. Dependency count = local edges + prerequisites. No response-wide limits. | — |
| Note 4.2 | Staged authoring. Generated identifiers. Plans ordered by prerequisite. | — |
| Proposal v1 | Hosted in terrastep, as a new `type: plan` with its own body. | v2: a layer on `type: design`, no new type, a flag instead of an escalation. |
| Proposal v2 | This document. | — |

---

## 3. Concepts

| Term | Meaning |
|---|---|
| **Design document** | A terrastep document with `type: design`. Brain budget measures these, and only these. |
| **Evaluation element** | A terrastep blocker (`B1`, `B2`, …) or question (`Q1`, `Q2`, …): a heading or bold run-in with an ID, plus a recommendation. Each one asks the reviewer to accept or change a recommendation. terrastep already parses them; its code calls them "items" (`core.parse_items`, the `body-items` code). This proposal says "evaluation element" because "item" does not say what the thing is for. |
| **Blocker** | An evaluation element in `## Blockers`. It carries `[open]` or `[resolved]`. An `[open]` blocker stops `status: ready`. This is terrastep's existing rule. |
| **Question** | An evaluation element in `## Questions`. It does not block `ready`. |
| **Edge** | A direct constraint between two evaluation elements in the same design, declared in the ledger. Its `type` is `coupled` or `sequencing`. |
| **Coupled** | The two evaluation elements must be judged together. |
| **Sequencing** | One evaluation element supplies a contract. The other evaluation element uses it without reopening the supplier. |
| **Prerequisite** | Another design document that this one needs, with a **contract** that states what it must supply. Declared in `depends_on`. |
| **Coupled cluster** | A connected group of evaluation elements joined by coupled edges. |
| **Measure / limit** | A count that terrastep computes, and its maximum from `terrastep.toml`. |
| **In budget** | Every measure is at or below its limit. The flag is shown in the Complexity box and in reports. |
| **Policy** | The effective set of four limits. |
| **Format** | What terrastep's code defines for the brain budget layer: the ledger schema, the Complexity box, the counting methods, and the YAML rules. |
| **Identity stamp** | `policy_id` and `schema_version` in the ledger. terrastep writes them. |
| **Tool-owned content** | The identity stamps and the Complexity box. Only `terrastep design scaffold` and `terrastep design render` write them. |
| **Retry** | One round of changes made after a precheck or check reported a failure or an over-budget measure, followed by a new run. |

---

## 4. The four measures

### 4.1 The measures and their default limits

| Machine name | Label in the box | Definition | Default limit |
|---|---|---|---:|
| `evaluative_count` | Evaluative count | Blocker and question evaluation elements in the document, open or resolved | 10 |
| `dependency_edge_count` | Dependency edge count | Edges plus `depends_on` entries | 11 |
| `largest_coupled_cluster_size` | Largest coupled cluster size | Evaluation elements in the largest coupled cluster | 3 |
| `word_count` | Word count | Words from the H1 to the end of Sequencing, without the Complexity box | 2000 |

### 4.2 What becomes an evaluation element

**The section decides the type.** No field says "this is a decision" or "this is a question":

- An evaluation element that must be settled or verified before implementation starts goes in **Blockers**, tagged
  `[open]` (or `[resolved]` once the owner settles it).
- Any other choice the reviewer must accept or change goes in **Questions**. A decision that does not
  block belongs here. Each terrastep question already carries a recommended answer.

Rules for what must be an evaluation element:

- **Every consequential choice is an evaluation element.** A choice is consequential when another plausible answer
  would change behavior, a public contract, persistent state, access control, or the implementation
  approach. A recommended default still counts. Helper names and import order are not evaluation elements.
- **An assumption the reviewer must judge is an evaluation element.** It is a blocker if it must be verified before
  work starts, and a question if it need not be. Its recommendation says how it will be verified or
  why it is acceptable.
- **Text that is not an evaluation element is design context.** It is not counted. An assumption or choice left in
  prose is a hidden evaluation element, just as an undeclared choice inside a coding step is.
- **Do not merge independent evaluation elements** to lower the count.
- **Resolved blockers still count.** The reviewer still reads and accepts them. And changing a tag must
  never lower a count.

### 4.3 Declaring edges

An edge is a direct constraint between two evaluation elements in the same design: the answer to one changes the
possible answers, required behavior, or acceptance criteria of the other. Two evaluation elements about the same
topic do not need an edge for that reason alone.

For each pair of evaluation elements, the model asks:

> If the answer to the first evaluation element changed, would I have to reconsider the answer to the second? What
> specific constraint would change?

If yes, it declares an edge and writes the constraint in `contract`. If no, it declares nothing. It
applies the test in both directions, then picks a `type`:

- **`sequencing`**: one evaluation element supplies a contract that the other uses without reopening the supplier.
  `from` is the supplier. `to` is the consumer.
- **`coupled`**: the evaluation elements must be judged together because their tradeoffs or validity constrain each
  other. If the constraint runs one way, use that direction. If it is mutual, write one edge with the
  lower ID first (blockers before questions, then by number). Never write the reverse copy. **If it is
  uncertain whether they can be judged separately, use `coupled`.**

Further rules:

- Declare **direct** constraints only. If Q1 constrains Q2 and Q2 constrains Q3, do not add Q1 → Q3
  because that path exists. Add it only if a separate constraint from Q1 applies directly to Q3.
- One record per pair. A coupled relationship replaces a sequencing record for the same pair.

Examples:

```yaml
edges:
  - from: Q1
    to: Q2
    type: coupled
    contract: Durable retry recovery needs persistent state. Storage durability and recovery guarantees must be chosen together.
```

Here Q1 asks where retry state lives, and Q2 asks whether retries survive a process restart. The edge
exists because durable recovery rules out state held only in memory. "Both are about retries" would
not justify it.

- **Sequencing:** Q1 selects the exported fields and Q2 selects the column order. Q2 orders what Q1
  selects, and the order cannot change which fields Q1 requires. Declare `Q1 → Q2`, `sequencing`.
- **No edge:** a download filename convention and the column order.

### 4.4 Declaring prerequisites (`depends_on`)

A prerequisite means this design cannot deliver its behavior until another design supplies a specific
interface, invariant or capability. The model asks: "What must that other design provide for this one
to work?" It records the other document's filename and that contract, once.

- Do not add a prerequisite because another design comes earlier in the work order, sits nearby, or
  covers the same feature.
- Do not copy the other design's evaluation elements, and do not draw edges to evaluation elements in another file.
- **If this design's choices could invalidate the other design's contract, the evaluation elements are coupled,
  not sequenced.** Put them in one design. Do not invent a prerequisite boundary to lower a cluster.
- A contract says what this design needs. It does not claim that the prerequisite is implemented or
  approved.

### 4.5 How terrastep computes each measure

```python
elements = core.parse_items(blockers_section) + core.parse_items(questions_section)
evaluative_count = len(elements)
dependency_edge_count = len(ledger["edges"]) + len(ledger["depends_on"])
largest_coupled_cluster_size, members = largest_coupled_cluster([e.ident for e in elements], ledger["edges"])
word_count = len(counted_text.split())
```

`dependency_edge_count` is deliberately coarse: local evaluation element relationships plus incoming contracts. A
design is charged only for the prerequisites that it declares, not for designs that depend on it. So
every design's count is computed without a global graph.

`largest_coupled_cluster_size` builds an undirected graph. The graph has every evaluation element and only the edges
with `type: coupled`. The measure is the node count of the largest connected component:

```python
def largest_coupled_cluster(element_ids, edges):
    neighbors = {element_id: set() for element_id in element_ids}
    for edge in edges:
        if edge["type"] == "coupled":
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
            largest, members = len(component), sorted(component)
    return largest, members
```

- No evaluation elements gives 0. Isolated evaluation elements give 1.
- Coupled edges Q1–Q2 and Q2–Q3 give 3, even without a Q1–Q3 edge.
- A sequencing edge does not enlarge a cluster.
- The function returns the members, so an over-budget report can name the actual group.

`word_count` is `len(text.split())` over the raw Markdown from the H1 line through the end of
`## Sequencing`, with the whole Complexity section removed. Headings, code and list markers count. The
frontmatter and the dated sections after Sequencing do not. This is a stable formatting measure, not a
linguistic word count.

### 4.6 What the measures do not establish

- That every consequential choice or assumption became an evaluation element.
- That a declared constraint is real, or that a `sequencing` edge should not be `coupled`.
- That a prerequisite's contract is true or implemented.
- That a design within budget is correct, complete, or approved.

Before each check, the model rereads the design and asks which choices or assumptions it has not made
into evaluation elements, and which evaluation elements depend on each other without an edge. A second pass in a fresh context that
asks only "What choices or assumptions does this design contain that are not evaluation elements?" makes this
stronger. It is optional here (section 16).

---

## 5. The document format

### 5.1 Which documents

- **`type: design`**: measured, when the repository enables brain budget.
- **`type: note`** and **`type: legacy`**: never measured. A note is a passive read with no evaluation elements. A
  legacy document is history.
- To keep type from becoming an escape route, terrastep warns when a `note` or `legacy` document has a
  `## Blockers` or `## Questions` section. The skill also states that planning requests always produce
  design documents.

A design is a normal terrastep document: `NNNN_slug.md` inside `scan_dirs`, numbered by
`terrastep next-id` (or by `terrastep design scaffold`). One design per file. It appears in `STATUS.md`
as today.

### 5.2 The ledger

The frontmatter has the usual terrastep keys and one `brain_budget` mapping:

```yaml
brain_budget:
  schema_version: sha256:6c16c11afcf0
  policy_id: sha256:4a30b1da8ac7
  depends_on:
    - file: 0007_transaction_query_contract.md
      contract: The query returns every authorized, filtered row in the requested sort order.
  edges:
    - from: Q1
      to: Q2
      type: sequencing
      contract: Q2 orders the field set that Q1 selects. The order cannot change which fields Q1 selects.
```

The evaluation elements themselves are **not** in the ledger. They exist once, in the body, where terrastep already
reads them. The ledger holds only what the body cannot express: the identity stamps, the edges, and
the prerequisites.

| Field | Written by | Rule |
|---|---|---|
| `schema_version` | tool | Equals the running terrastep's brain budget format identity (section 6). |
| `policy_id` | tool | Equals the identity of the effective limits in `terrastep.toml`. |
| `depends_on[]` | model (entries created by `scaffold --depends-on`) | `{file, contract}`. `file` is a bare filename, `NNNN_slug.md`, that resolves to a scanned design document. One entry per target. Not this file. |
| `edges[]` | model | `{from, to, type, contract}`. `from` and `to` are IDs of evaluation elements present in this document's body. |

Every text value is a non-empty string with at least one character that is not whitespace. Unknown
fields are errors.

### 5.3 The YAML rules inside `brain_budget`

terrastep reads frontmatter with `yaml.safe_load`. That call accepts a duplicate key (the last value
wins), resolves aliases, and turns an unquoted `2026-09-28` into a date object. terrastep needs that
date conversion for `status_changed` (`core.is_iso_date`). So these stricter rules apply **only inside
the `brain_budget` value**:

- It is a mapping with string keys.
- No duplicate key in any mapping.
- No anchor, alias or merge key (`<<`).
- No custom tag. Only JSON-compatible values are allowed, so an unquoted date is rejected.

Keys outside `brain_budget` keep today's behavior.

### 5.4 The ledger schema

terrastep's code owns this JSON Schema 2020-12 document. The `jsonschema` library accepts it
(`Draft202012Validator.check_schema`). The worked example passes it. A ledger that uses `kind` instead
of `type`, or an edge to `D2`, fails it with a precise path.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "policy_id", "depends_on", "edges"],
  "properties": {
    "schema_version": {"const": "sha256:6c16c11afcf0"},
    "policy_id": {"$ref": "#/$defs/identity"},
    "depends_on": {"type": "array", "items": {"$ref": "#/$defs/prerequisite"}},
    "edges": {"type": "array", "items": {"$ref": "#/$defs/edge"}}
  },
  "$defs": {
    "text": {"type": "string", "minLength": 1, "pattern": "\\S"},
    "identity": {"type": "string", "pattern": "^sha256:[0-9a-f]{12}$"},
    "document_file": {"type": "string", "pattern": "^[0-9]{4}_[^/\\\\]+\\.md$"},
    "element_id": {"type": "string", "pattern": "^[BQ][1-9][0-9]*$"},
    "prerequisite": {
      "type": "object",
      "additionalProperties": false,
      "required": ["file", "contract"],
      "properties": {
        "file": {"$ref": "#/$defs/document_file"},
        "contract": {"$ref": "#/$defs/text"}
      }
    },
    "edge": {
      "type": "object",
      "additionalProperties": false,
      "required": ["from", "to", "type", "contract"],
      "properties": {
        "from": {"$ref": "#/$defs/element_id"},
        "to": {"$ref": "#/$defs/element_id"},
        "type": {"enum": ["coupled", "sequencing"]},
        "contract": {"$ref": "#/$defs/text"}
      }
    }
  }
}
```

- The `const` value is never written in source code. terrastep computes it and inserts it at load time
  (section 6.3).
- `policy_id` only gets a format check here. Its value is compared separately with the effective
  limits, because the schema belongs to the package and must not depend on one repository's
  configuration.
- Limits never appear as `maxItems`. A valid design that is over budget is a different result from a
  malformed design.

### 5.5 The body

The body is **terrastep's design format, unchanged**, plus one tool-owned section:

- One H1, then front sections. terrastep requires a non-empty `summary` or `motivation` section, and
  warns when `design` or `scope` is missing.
- **`## Complexity`: the last front section, immediately before `## Blockers`.** terrastep writes it.
  terrastep's role table gains a `complexity` role, so this heading is recognized. Without the role,
  it produces an "unclassified front section" warning, which is today's behavior.
- Exactly `## Blockers`, `## Questions`, `## Recommendations`, `## Sequencing`, in that order, with
  every existing terrastep rule: evaluation element IDs, one `[open]`/`[resolved]` tag per blocker, a recommendation
  per evaluation element, coverage of every open evaluation element in Recommendations, and the `ready` gate on open blockers.
- Dated sections after Sequencing, as today (for example `## What was built (2026-10-02)`).
- The scaffold puts the draft marker `<!-- terrastep:draft -->` into each section the model must fill.
  The final check rejects the marker anywhere in the file.

### 5.6 The Complexity box

Within budget:

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

Over budget, only the flag line changes. It names each measure that is over, and the cluster members:

```markdown
**Within budget: no.** Over: largest coupled cluster size 4 > 3 (B1, Q1, Q2, Q3).
```

The rows, labels, columns and flag wording are fixed. `terrastep design render` writes the whole box.
The model never writes or edits it. `terrastep check` recomputes every value and fails `brain-budget-complexity`
if the box is missing, misplaced, or stale.

### 5.7 What the scaffold writes

`terrastep design scaffold --title "Add the CSV download" --slug csv_download --dir journal/plans/v0.2
--depends-on 0007_transaction_query_contract.md` writes:

````markdown
---
status: planning
status_changed: 2026-09-29
type: design
next: Owner reviews.
brain_budget:
  schema_version: sha256:6c16c11afcf0
  policy_id: sha256:4a30b1da8ac7
  depends_on:
  - file: 0007_transaction_query_contract.md
    contract: <!-- terrastep:draft -->
  edges: []
---
# Add the CSV download

## Summary
<!-- terrastep:draft -->

## Scope
<!-- terrastep:draft -->

## The design
<!-- terrastep:draft -->

## Verification
<!-- terrastep:draft -->

## Complexity

## Blockers
<!-- terrastep:draft -->

## Questions
<!-- terrastep:draft -->

## Recommendations
<!-- terrastep:draft -->

## Sequencing
<!-- terrastep:draft -->
````

The front sections are terrastep's required role (`summary`) and its expected roles (`design`,
`scope`), plus `Verification`. A scaffold is incomplete on purpose. An empty Blockers or Questions
section does not mean the feature has no evaluation elements. The model must investigate and write the evaluation elements before
the first precheck.

### 5.8 Worked example

A user asks: "Add a CSV export of the transaction view that keeps its filters and sort order." The
agent splits the work into three designs (section 10.9). This is the second one,
`journal/plans/v0.2/0008_csv_download.md`. It depends on `0007_transaction_query_contract.md`, which
already passes `terrastep check`.

````markdown
---
status: planning
status_changed: 2026-09-29
type: design
next: Owner reviews.
brain_budget:
  schema_version: sha256:6c16c11afcf0
  policy_id: sha256:4a30b1da8ac7
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
````

How the numbers follow:

- Evaluative count 3: B1, Q1, Q2.
- Dependency edge count 2: one edge plus one prerequisite.
- Largest coupled cluster size 1: the only edge is `sequencing`.
- Word count 245: computed from `# Add the CSV download` through Sequencing, without the Complexity
  box.

**Checked against terrastep 0.1.0 today:** `terrastep check` on this file prints `OK: 1 document(s)
pass`. Its only warning is `unclassified front sections: ['Complexity']`, which the new `complexity`
role (section 5.5) removes. So the brain budget layer adds to terrastep's format without breaking any
existing rule.

The design is within budget, but it cannot become `ready` while B1 is `[open]`. terrastep's existing
`gate-open-blocker` rule enforces that.

"Return the result as a CSV attachment" deliberately does not add "with a dated filename." A filename
convention is a choice, so it would have to be an evaluation element.

### 5.9 The `In budget` column in `STATUS.md`

`terrastep build` writes one more column into every table of the index (Active, Planning, and All),
after `Status`. The column is permanent: it is present in every repository, even when brain budget is
off.

| Value | When |
|---|---|
| `yes` | A design in `planning` or `ready`, brain budget is on, and every measure is at or below its limit. |
| `no` | The same, but at least one measure is over its limit. |
| `NA` | The budget is not active for this document: brain budget is off, the document is not a design, the design's status is `in-progress`, `implemented` or `closed` (section 7.5), or its measures cannot be computed because the document is malformed (and `terrastep check` reports that). |

For example, with brain budget on:

```markdown
| Changed | No. | Doc | Type | Status | In budget | Next |
|---|---|---|---|---|---|---|
| 2026-09-29 | 0009 | [0009_export_action.md](v0.2/0009_export_action.md) | design | planning | no | Owner reviews. |
| 2026-09-29 | 0008 | [0008_csv_download.md](v0.2/0008_csv_download.md) | design | planning | yes | Owner reviews. |
| 2026-09-28 | 0002 | [0002_claude_skill.md](v0.1/0002_claude_skill.md) | design | implemented | NA | None. Sequencing steps 1-7 are done. |
```

Three consequences follow from terrastep's existing `stale-index` rule. `terrastep check` fails when
`STATUS.md` differs from what `terrastep build` would write:

- After an upgrade, a repository's `STATUS.md` is stale until someone runs `terrastep build` once.
  Today this affects only terrastep's own repository, because terrastep has not been distributed
  (OQ10).
- An edit that moves a design across a limit changes its value, so `terrastep build` must run again.
  A status change already works this way today.
- A limit change in `terrastep.toml` can change many values at once, and the same fix applies.

A design's own Complexity box keeps the flag from its last render. That lets a reader see how an
`implemented` design scored when it was approved, while its index entry reads `NA`.

---

## 6. Identity: generated `policy_id` and `schema_version`

### 6.1 Why the identifiers are generated

A hand-written label such as `file-plan-v1` is not tied to the values it names. If a maintainer changes
a limit but keeps the label, every document that carries the label now means the new limits, and no
check notices. A hash of the content cannot drift from the content. **terrastep's code manages these
identifiers. No person creates them.** A person reads them in the frontmatter to audit a document and
to spot a difference.

### 6.2 `policy_id`

`policy_id` is the identity of the **effective** limits: all four measures, after defaults are applied
to what `terrastep.toml` lists. Writing the defaults explicitly and omitting them give the same
`policy_id`. `enabled` and `max_retries` are not part of the policy. They control the workflow, not
what a document is measured against.

### 6.3 `schema_version`

`schema_version` is the identity of the brain budget layer's **format definition**, as terrastep's code
owns it:

```python
FORMAT_DEFINITION = {
    "ledger_schema": BASE_SCHEMA,  # section 5.4, without properties.schema_version
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
```

- It covers more than the schema, because a change in counting re-scores documents as surely as a
  schema change does.
- A schema cannot contain a hash of itself. So `BASE_SCHEMA` leaves out `properties.schema_version`.
  terrastep hashes `FORMAT_DEFINITION`, then builds the working schema as `BASE_SCHEMA` plus
  `"schema_version": {"const": <hash>}`.
- terrastep's own design rules (Blockers, Questions, Recommendations, Sequencing) are not part of this
  hash. The terrastep version already versions them, as it does today.
- Because the definition belongs to the package, `schema_version` changes only when a terrastep
  release changes the layer. `terrastep skill build` writes the current value into the generated
  reference, and the existing staleness test catches a change that was not regenerated.

### 6.4 Canonical form and golden values

```python
import hashlib, json

def identity(value) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
```

- Sorted keys and no insignificant whitespace, so reordering or reformatting `terrastep.toml` changes
  nothing. For this content, the result is the same as RFC 8785 canonical JSON.
- Twelve hexadecimal characters (48 bits) avoid an accidental collision within one project. They are
  not meant to resist a deliberate forgery.
- **Golden values**, computed for this proposal:

| Input | Identity |
|---|---|
| Default limits `{"dependency_edge_count":11,"evaluative_count":10,"largest_coupled_cluster_size":3,"word_count":2000}` | `policy_id` **`sha256:4a30b1da8ac7`** |
| The same with `word_count = 2500` | `policy_id` `sha256:cfd3b3f6f3d5` |
| `FORMAT_DEFINITION` exactly as written in section 6.3 | `schema_version` `sha256:6c16c11afcf0` |

The `schema_version` value holds only while the implementation keeps that exact definition. Any change
to it gives a new value, which is the purpose. Tests pin the two `policy_id` values.

### 6.5 Where the identifiers live

**Only in each design's frontmatter.** They are never stored in `terrastep.toml`:

- terrastep computes them from their sources every time it runs. A value that is never stored cannot
  go stale.
- `terrastep.toml` is written by a person. The TOML libraries that terrastep uses (`tomllib`, and
  `tomli` on Python 3.10) can only read. Writing a computed value back would need a new dependency
  (`tomli-w`), and a tool would edit a file that a person maintains.

`terrastep design budget` prints both current values, so a person can compare them with any document's
stamps.

### 6.6 Who writes and checks them, and what a mismatch means

- `terrastep design scaffold` writes both stamps.
- `terrastep design render` rewrites both to the current values, after the ledger passes the current
  schema.
- `terrastep design precheck` and `terrastep check` compare them with the current values, for designs
  in `planning` or `ready` (section 7.5).

A mismatch means "this design was last rendered under a different policy or format." terrastep does
**not** quietly re-score it. The fix is explicit, and it appears in the git diff: run
`terrastep design render` (it re-stamps and rewrites the box), then `terrastep check`.

### 6.7 Why two identifiers

- `schema_version` differs: the ledger's **shape** may no longer be valid. Render, and possibly fix the
  ledger.
- Only `policy_id` differs: only the **thresholds** changed. Render and check again. The flag may
  change.

One combined hash could not tell these apart, and it would make every limit adjustment look like a
format change. The per-run digests in reports (section 7.8) are a third, separate thing: a receipt for
one run.

### 6.8 The step that still depends on a person

The measure-method IDs (`"coupled-components-v1"`, …) are constants that a maintainer changes when a
counting algorithm changes. A hash cannot capture what an algorithm means. Golden fixtures with
expected measures guard this step: a counting change fails them, which tells the maintainer to change
the method ID.

---

## 7. Validation

### 7.1 Two stages

| Stage | Run by | Checks | Does not check |
|---|---|---|---|
| **Declarations** | `terrastep design precheck` | terrastep frontmatter keys. The ledger (YAML rules, identity, schema). The evaluation elements in Blockers and Questions (terrastep's `body-items`, `body-tag`, `body-recommend`, `body-empty` for those two sections). Edges and cycles. Prerequisites. Draft markers in the ledger, Blockers and Questions. The three structural measures. | Front sections, Recommendations coverage, Sequencing, `word_count`, the Complexity box, draft markers elsewhere |
| **Final** | `terrastep check` (so also the pre-commit hook and the Stop hook) | Every terrastep design rule, every brain budget layer rule, and all four measures | — |

Both stages call the same functions. The structural measures from a precheck and a final check are
always identical. A passing precheck never counts as final validation.

### 7.2 Brain budget layer rules

These apply to designs in `planning` or `ready` when brain budget is enabled. terrastep's existing
design rules apply as today. When a rule fails, terrastep suppresses rules that would only repeat
that failure.

1. **Ledger present:** `brain_budget` exists and is a mapping (`brain-budget-ledger-missing`).
2. **YAML rules** from section 5.3 (`brain-budget-yaml-strict`). If this fails, stop.
3. **Format identity:** `schema_version` equals the current value (`brain-budget-schema-version`). If this fails,
   stop. Render first.
4. **Schema** (`brain-budget-schema`), with a path such as `brain_budget.edges[1].type`.
5. **Policy identity:** `policy_id` equals the current value (`brain-budget-policy-id`).
6. **Edges** (`brain-budget-edge`): both endpoints are evaluation elements in this document's body. No self-edge. No duplicate
   ordered pair. No reverse copy of a coupled pair. No sequencing record for a pair that is already
   coupled.
7. **Sequencing cycle** (`brain-budget-cycle`): after each coupled cluster becomes one node, the sequencing edges
   have no cycle.
8. **Prerequisites** (`brain-budget-prereq`): each `file` names a scanned design document; it is not this file;
   each target appears once. Across all designs, `depends_on` has no cycle (`brain-budget-prereq-cycle`, reported
   on every design in the cycle).
9. **Draft markers** (`brain-budget-draft-marker`): anywhere in the file (final), or in the ledger, Blockers and
   Questions (precheck).
10. **Complexity box** (`brain-budget-complexity`, final only): present, last front section, just before Blockers,
    and exactly what `render` would write.

Measures over their limits are **not** failures (section 7.6).

### 7.3 Rules across documents

terrastep always loads every document in `scan_dirs`, even when `terrastep check` reports only
selected files (`core.check_docs`). So prerequisite existence and cycle rules always run.
`dependency_validation` in a report is always `passed` or `failed`.

These are **warnings**, not failures:

- A prerequisite design currently fails `terrastep check`. That failure is reported on the prerequisite
  itself.
- A `note` or `legacy` document has a `## Blockers` or `## Questions` section (section 5.1).

### 7.4 Why only designs

Only `type: design` gets the layer. Notes and legacy documents carry no evaluation elements to judge (section 5.1).

### 7.5 Which statuses get the layer

Limits and the format change over time. Re-measuring approved or finished designs after each change
would fail the repository's history. So:

| Status | Brain budget layer rules |
|---|---|
| `planning` | All (section 7.2), plus the measures and the flag. |
| `ready` | All. Approval needs a design that is current with the policy and format. |
| `in-progress`, `implemented`, `closed` | None. terrastep's existing rules apply as today (for example `gate-open-blocker`, `body-history`). |

A design that becomes `ready` while `in_budget` is `false` is allowed. The flag informs the owner. It
does not overrule the owner.

### 7.6 The budget is a flag

- When all four measures are at or below their limits, `in_budget` is `true`.
- When any measure is over, `in_budget` is `false`. The Complexity box says so and names the measures
  and the cluster members. `terrastep check` prints a warning, for example
  `WARN: …/0009_export_action.md: over budget: largest coupled cluster size 4 > 3 (B1, Q1, Q2, Q3)`.
- A warning never fails `terrastep check`, so the pre-commit hook and the Stop hook never block an
  over-budget design.
- **Format rules stay hard.** A malformed design fails, whether or not it is in budget.

Because nothing fails when a design is over budget, the honesty rules carry the weight (section
10.10). A model that deletes a real evaluation element, or relabels a coupled edge as sequencing, gets
`in_budget: true` at no cost. Section 15 audits for this.

### 7.7 Failure codes

New entries for `core.FAILURE_CODES`. Each name follows the convention of the place where it appears.
Failure codes are kebab-case, like terrastep's existing codes, so they start with `brain-budget-`.
Python names, TOML keys and YAML keys use `brain_budget`. The existing registry test checks
every `Finding(...)` code in `src/terrastep/*.py`, so it covers these.

| Code | Meaning |
|---|---|
| `brain-budget-ledger-missing` | A design in `planning` or `ready` has no `brain_budget` mapping while brain budget is enabled. `terrastep design render` adds one. |
| `brain-budget-yaml-strict` | `brain_budget` has a duplicate key, an anchor, alias or merge key, a custom tag, or a value that is not a JSON type (for example an unquoted date). |
| `brain-budget-schema-version` | `schema_version` does not match this terrastep's brain budget format. Run `terrastep design render`. |
| `brain-budget-schema` | `brain_budget` does not match the ledger schema. |
| `brain-budget-policy-id` | `policy_id` does not match the limits in `terrastep.toml`. Run `terrastep design render`, then check again. |
| `brain-budget-edge` | An edge names an evaluation element that is not in the body, joins an evaluation element to itself, or repeats a relationship that is already declared. |
| `brain-budget-cycle` | Sequencing edges form a cycle after coupled evaluation elements are grouped. |
| `brain-budget-prereq` | A `depends_on` entry names a file that is not a scanned design document, names this file, or repeats another entry. |
| `brain-budget-prereq-cycle` | Designs depend on each other in a cycle. |
| `brain-budget-draft-marker` | A scaffold draft marker is still present. |
| `brain-budget-complexity` | The Complexity box is missing, not placed just before Blockers, or not what `terrastep design render` would write. |

Existing codes that keep their meaning for budgeted designs: every `fm-*` code, `body-order`,
`body-roles`, `body-empty`, `body-items`, `body-tag`, `body-recommend`, `body-r-cover`, `body-dated`,
`gate-open-blocker`, `body-history`, and `stale-index`.

### 7.8 Reports and exit codes

| Exit code | Meaning |
|---|---|
| 0 | No failures. Warnings, including over-budget warnings, are allowed. |
| 1 | At least one failure, or a verb refused to write (scaffold, render). |
| 2 | Configuration error (an invalid `[brain_budget]`) or usage error. `argparse` already exits 2 for usage errors. |

**Text output** does not change: `FAIL: <file>: [<code>] <message>`, `WARN: <file>: <message>`, then
the summary line.

**`terrastep design precheck FILE --format json`** (the third design in section 10.9):

```json
{
  "file": "journal/plans/v0.2/0009_export_action.md",
  "stage": "declarations",
  "declarations_valid": true,
  "structural_in_budget": false,
  "format_valid": null,
  "in_budget": null,
  "policy_id": "sha256:4a30b1da8ac7",
  "schema_version": "sha256:6c16c11afcf0",
  "measures": {"evaluative_count": 4, "dependency_edge_count": 5,
               "largest_coupled_cluster_size": 4, "word_count": null},
  "limits": {"evaluative_count": 10, "dependency_edge_count": 11,
             "largest_coupled_cluster_size": 3, "word_count": 2000},
  "over_budget": [{"measure": "largest_coupled_cluster_size", "actual": 4, "limit": 3,
                   "members": ["B1", "Q1", "Q2", "Q3"]}],
  "deferred_checks": ["front_sections", "recommendations_coverage", "sequencing",
                      "word_count", "complexity_box", "draft_markers_outside_elements"],
  "failures": [],
  "warnings": ["over budget: largest coupled cluster size 4 > 3 (B1, Q1, Q2, Q3)"]
}
```

If the ledger prevents a measure from being computed, that measure and `structural_in_budget` are
`null`, not zero.

**`terrastep check [FILES] --format json`:**

```json
{
  "terrastep_version": "0.2.0",
  "config_file": "terrastep.toml",
  "config_sha256": "<64 hex characters of the terrastep.toml bytes, or null>",
  "ok": false,
  "summary": {"documents": 1, "failures": 1, "warnings": 0},
  "documents": [
    {
      "file": "journal/plans/v0.2/0008_csv_download.md",
      "type": "design",
      "status": "planning",
      "failures": [
        {"code": "brain-budget-edge", "message": "edges[0].to names Q3, which is not an evaluation element in this document.",
         "path": "brain_budget.edges[0].to", "expected": "an evaluation element ID in Blockers or Questions",
         "actual": "Q3"}
      ],
      "warnings": [],
      "brain_budget": {
        "stage": "final",
        "format_valid": false,
        "in_budget": true,
        "over_budget": [],
        "open_blockers": ["B1"],
        "dependency_validation": "passed",
        "policy_id": "sha256:4a30b1da8ac7",
        "schema_version": "sha256:6c16c11afcf0",
        "measures": {"evaluative_count": 3, "dependency_edge_count": 2,
                     "largest_coupled_cluster_size": 1, "word_count": 245},
        "limits": {"evaluative_count": 10, "dependency_edge_count": 11,
                   "largest_coupled_cluster_size": 3, "word_count": 2000},
        "file_sha256": "<64 hex characters of the file bytes>"
      }
    }
  ],
  "corpus": {"failures": [], "warnings": []}
}
```

- Every document in scope appears. Only budgeted designs have a `brain_budget` block.
- `path`, `expected` and `actual` are `null` for codes that do not have them. This includes all
  existing terrastep codes.
- `in_budget` is `null` when a malformed document prevents measurement.
- `corpus` carries results that belong to no single document: `stale-index` and the in-progress cap.
- `file_sha256`, `config_sha256`, `terrastep_version`, `policy_id` and `schema_version` form the
  **receipt** of the run. An edit to the file or the configuration makes an earlier receipt invalid.
  The receipt is only in the report. Nothing stores it.

### 7.9 Diagnostics

- Every failure has a stable code, the file, and, where one exists, a precise location (a ledger path,
  or a body section) with expected and actual values.
- Independent failures are reported together, so one retry can fix them all. Failures that only follow
  from an earlier one are suppressed.
- An over-budget cluster names its members.
- Output stays compact. terrastep never repeats the whole file, policy or schema.
- Code never invents an evaluation element and never changes an edge type. Only the stamps and the Complexity box are
  written by a tool.

---

## 8. Configuration: `[brain_budget]` in `terrastep.toml`

```toml
scan_dirs = ["journal/plans"]

[brain_budget]
enabled = true
max_retries = 2

[brain_budget.limits]
evaluative_count = 10
dependency_edge_count = 11
largest_coupled_cluster_size = 3
word_count = 2000
```

| Key | Default | Meaning |
|---|---|---|
| `[brain_budget] enabled` | `false` | Turns on the brain budget layer for `type: design`. |
| `[brain_budget] max_retries` | `2` | Retries per design, shared between precheck and check, for fixing failures and for trying a different split to fit the budget. It bounds the agent's token spend. The agent follows it; terrastep does not count it (section 10.6). |
| `[brain_budget.limits] evaluative_count` | `10` | Section 4.1. |
| `[brain_budget.limits] dependency_edge_count` | `11` | Section 4.1. |
| `[brain_budget.limits] largest_coupled_cluster_size` | `3` | Section 4.1. |
| `[brain_budget.limits] word_count` | `2000` | Section 4.1. |

**Validation.** terrastep ignores unknown top-level keys today (`config.load` reads keys with
`data.get`). The new tables are strict, because a misspelled limit would otherwise have no effect:

- An unknown key in `[brain_budget]` or `[brain_budget.limits]` is a configuration error that names the
  key.
- `enabled` must be a boolean. `max_retries` and each limit must be an integer ≥ 0. A boolean is
  rejected even though Python treats `true` as 1.
- A configuration error exits 2 before any document is checked.

**Not configurable:** the ledger schema, the Complexity box, the counting methods, the YAML rules, and
the draft marker. terrastep generates its skill from package constants at build time and ships it
through pip. A per-repository format could not appear in that shared skill. terrastep already fixes
the design format in code; configuration only sets scope and thresholds.

New entries for `config.CONFIG_HELP` supply the generated configuration table.

---

## 9. CLI verbs

### 9.1 Verb table

| Verb | What it does | Writes | Exit codes |
|---|---|---|---|
| `terrastep design budget [--format json]` | Prints whether brain budget is on, the effective limits (marking defaults), `max_retries`, `policy_id`, `schema_version`, and the terrastep version. | Nothing | 0; 2 |
| `terrastep design scaffold --title T [--slug S] [--dir D] [--depends-on FILE …]` | Creates a new design skeleton with the next free number. With brain budget on, it adds the ledger and an empty Complexity section. | One new file. Never overwrites. | 0; 1 on refusal; 2 |
| `terrastep design precheck FILE [--format json]` | Runs the declarations stage (section 7.1). | Nothing | 0; 1; 2 |
| `terrastep design render FILE` | Writes the tool-owned parts: the two stamps and the Complexity box. Adds the ledger and the box to a design that lacks them. Keeps every other byte. | That file, only if something changed | 0; 1 on refusal; 2 |
| `terrastep check [FILES] [--if-changed] [--format json]` | Existing verb. Now also runs the brain budget layer. | Nothing | 0; 1; 2 |
| `terrastep build` | Existing verb. The index now has the permanent `In budget` column (section 5.9). | `STATUS.md` | As today |
| `terrastep next-id`, `survey`, `migrate`, `install-hooks`, `skill`, `hook` | Unchanged. | As today | As today |

`design` follows the same pattern as `migrate propose|apply` and `skill build|install`. Every verb keeps
`--root` and `--config`. The final validation is `terrastep check`. There is no separate check
command, so the hooks and the agent run one validator.

### 9.2 `terrastep design budget`

Read-only. It works when brain budget is off (it reports `"enabled": false` and exits 0), so the skill
can use it to decide which procedure applies. The agent runs it before decomposing the work, because a
limit left at its default does not appear in `terrastep.toml`.

### 9.3 `terrastep design scaffold`

1. `--dir` defaults to `scan_dirs[0]`, and must be inside a `scan_dirs` entry.
2. The number is `core.next_id`. The file name is `NNNN_<slug>.md`. The default slug comes from the
   title: lower case, with other characters turned into `_`.
3. It writes the frontmatter with PyYAML's serializer, not from model memory: `status: planning`,
   today's `status_changed`, `type: design`, `next: Owner reviews.`, and, with brain budget on, the
   ledger (section 5.7).
4. **It enforces prerequisite order.** Each `--depends-on FILE` must resolve to a scanned design
   document that currently passes `terrastep check`. A prerequisite that is over budget is fine: it is
   valid, only flagged. Otherwise scaffold refuses, and it names the prerequisite and the reason.
5. It never overwrites a file, consistent with `install-hooks` and `skill install`.
6. With brain budget off, it still writes a plain design skeleton (no ledger, no Complexity section).
   That makes the verb useful to every terrastep repository.

### 9.4 `terrastep design precheck`

Read-only. It loads the whole scanned corpus so that the prerequisite rules can run. It exits 0 when
the declarations are valid, even when a structural measure is over budget (that is a warning). It exits
1 on a failure. It refuses (exit 1) when brain budget is off.

### 9.5 `terrastep design render`

1. **It refuses** (exit 1, writes nothing) when the frontmatter does not parse, when an existing ledger
   fails the YAML rules or the schema (stamp values are ignored for this test), or when the body
   structure is ambiguous: `## Blockers` is missing, or a code fence is left open. It lists the reasons.
   It also refuses when brain budget is off.
2. It replaces the `schema_version` and `policy_id` values in place. It uses the positions that PyYAML
   records on parsed nodes (`yaml.compose` marks). It does not re-serialize, so sibling keys, comments
   and quoting stay byte-for-byte the same.
3. If the ledger is missing, it appends one with the current stamps and empty `depends_on` and `edges`.
   This is how an existing `planning` design joins the budget.
4. It writes the Complexity box. If the section is missing, it inserts it just before `## Blockers`.
5. It writes honest values, including an over-budget flag. Rendering is not approval.
6. It is idempotent. A second run without edits produces identical bytes and reports "unchanged".
7. It allows draft markers in the body. Only the final check rejects them.

---

## 10. How an LLM writes design documents, step by step

This is the procedure the generated skill teaches (the text is in section 10.11). From the user's side
it is one chat turn. Underneath, the model runs terrastep commands, reads their JSON output, and edits
files, many times within that turn.

### 10.1 Preconditions

- The repository's `terrastep.toml` has `[brain_budget] enabled = true`.
- terrastep is installed, and the agent may run it and write files inside `scan_dirs`.
- The terrastep skill is installed (`terrastep skill install`).

If the agent cannot run terrastep or write files, it follows the procedure without the tools. It writes
one clearly labeled document per design, and it labels each one an **unvalidated draft**. It never says
files were written when it only displayed them, and it never claims a check that did not run.

### 10.2 Step 1: read the budget

```
terrastep design budget --format json
```

Use the limits and `max_retries` from this output. Do not assume the defaults, and do not copy the
limits into any file.

### 10.3 Step 2: investigate and decompose, before writing anything

1. Investigate the request and, when possible, the repository. Separate required work from optional
   work.
2. List every evaluation element for the **whole** request: each consequential choice and each assumption the
   reviewer must judge (section 4.2). For each, decide: must it be settled before work starts
   (blocker) or not (question)? Draft a recommendation.
3. Apply the pair test (section 4.3) to every pair. Mark each relationship `coupled`, `sequencing`, or
   none. When unsure, `coupled`.
4. Group the evaluation elements into designs:
   - A coupled cluster always stays in one design.
   - Split designs only across sequencing relationships that a stated contract supports.
   - Aim for each design to fit the limits.
5. If a coupled cluster is larger than the limit, keep it together anyway. That design will be flagged.
   Splitting coupled evaluation elements to pass is never allowed.
6. Make as many designs as the work needs. The number of designs is never a reason to drop required
   scope.

### 10.4 Step 3: order the designs

Sort the designs so that each one comes after every design it depends on. Designs with no dependency
between them can come in any order. A prerequisite must pass `terrastep check` before a design that
depends on it is scaffolded. `terrastep design scaffold` enforces this.

### 10.5 Step 4: the loop for each design, in prerequisite order

**a. Scaffold.**

```
terrastep design scaffold --title "Add the CSV download" --slug csv_download \
    --dir journal/plans/v0.2 --depends-on 0007_transaction_query_contract.md
```

**b. Read the prerequisites.** Open each prerequisite's file and read its actual contract and evaluation elements.
Use the file, not what the conversation remembers.

**c. Declare.** Write the evaluation elements in Blockers and Questions: an ID and title line (with the tag, for a
blocker) and a recommendation each. Fill the ledger: the edges, and a `contract` for each `depends_on`
entry. Do not touch the stamps or the Complexity section.

**d. Precheck.**

```
terrastep design precheck journal/plans/v0.2/0008_csv_download.md --format json
```

- A failure: patch what it names. That is one retry.
- Over budget: if an honest re-split exists (for example two groups joined only by a sequencing
  contract), try it. That is one retry. If the only excess is a coupled cluster, do not spend a retry:
  no honest split exists. Keep going. The design will be flagged.
- Do not write prose while the precheck fails.

**e. Write the prose.** Replace every draft marker. Front sections: summary, scope, the design,
verification. Recommendations: mention every open evaluation element by ID. Sequencing: the order of the work. If
writing reveals a new choice, assumption or dependency, make it an evaluation element or an edge, and precheck again.

**f. Render.**

```
terrastep design render journal/plans/v0.2/0008_csv_download.md
```

**g. Final check.**

```
terrastep check journal/plans/v0.2/0008_csv_download.md --format json
```

**h. Fix.** Patch only the fields or sections that the diagnostics name. Do not regenerate the file.
Render again if a patch changes a measure. Check again after the last edit.

**i. Done.** The design passes `terrastep check`. The Complexity box says whether it is within budget.

### 10.6 Retries

- `max_retries` (default 2) is **per design**, and the precheck and the check **share** it.
- A retry is one round of changes made after a precheck or check reported a failure or an over-budget
  measure, followed by a new run. Fixing several reported problems together is one retry.
- These are not retries: completing the scaffold, writing the first prose, and rendering.
- Renaming a design, restarting a stage, or moving the same scope to a new file does not reset the
  count.
- **When the retries run out:**
  - If the design passes every format rule, deliver it. If it is over budget, the Complexity box
    already says so.
  - If format failures remain, deliver it as a **failed draft** with its diagnostics. The pre-commit
    hook will not let it be committed. The Stop hook blocks the end of the turn once. On the second
    stop request (`stop_hook_active`), it lets the turn end, so the agent can report instead of
    looping.

terrastep does not count retries: `check` stays read-only, and terrastep keeps no state between runs.
`max_retries` is an instruction to the agent. Evaluation counts retries from session transcripts
(section 15).

### 10.7 What an over-budget design means

A design delivered with `in_budget: false` is not an error. It tells the owner: "this one is harder
than the standard, and the agent could not find an honest split within its retries." The report says
which measure is over and what split was tried (section 10.8). The owner can approve it as it is, ask
for a different split, or change the limits.

### 10.8 Step 5: finish and report

```
terrastep build
terrastep check
```

`terrastep build` regenerates `STATUS.md`; without it, `terrastep check` fails `stale-index`. The report
to the user links to the designs. It does not repeat them:

```text
Designs (in prerequisite order):
1. journal/plans/v0.2/0007_transaction_query_contract.md: valid, within budget.
   Open blockers: B1 (the query's authorization path is unverified).
2. journal/plans/v0.2/0008_csv_download.md: valid, within budget. Depends on 0007.
   Open blockers: B1 (streaming support).
3. journal/plans/v0.2/0009_export_action.md: valid, OVER BUDGET.
   Largest coupled cluster 4 > 3 (B1, Q1, Q2, Q3): these must be judged together.
   Split tried: progress reporting as its own design. Rejected: Q3 changes the answer to Q1.

terrastep check: passes (1 over-budget warning).
Not established by the checks: that every choice and assumption became an evaluation element.
```

| Delivery outcome | Evidence |
|---|---|
| **Valid design, within budget** | The exact final file passes `terrastep check`; the box says yes. |
| **Valid design, over budget** | The exact final file passes `terrastep check`; the box says no and names the measures. |
| **Failed draft** | Format failures remain after the retries. The report includes the diagnostics. |
| **Unvalidated draft** | terrastep was not available or could not run. No claim of compliance. |

### 10.9 Walkthrough: a request that needs three designs

A user asks: "Add a CSV export of the transaction view that keeps its filters and sort order." The next
free number is 0007. The defaults are in force.

1. `terrastep design budget --format json`.
2. The agent investigates and lists the evaluation elements: the row scope and authorization of the export query;
   the CSV fields and column order; streaming support; where the export control lives; synchronous or
   background work for large exports; progress reporting; and whether a background job runner is
   available. Row scope and authorization are sequenced before the CSV format. The CSV format is
   sequenced before the export action. So there are three designs: 0007 (query contract) → 0008 (CSV
   download) → 0009 (export action).
3. **0007.** Scaffold, declare, precheck (passes), write, render, check (passes). Within budget.
4. **0008.** Scaffold with `--depends-on 0007_transaction_query_contract.md`; scaffold accepts, because
   0007 passes. The agent reads 0007's file for the contract, declares B1, Q1, Q2 and one sequencing
   edge, and prechecks. It writes the prose. The first check fails `body-r-cover`: Recommendations does
   not mention Q2. That is one retry. The agent adds Q2 to Recommendations, and the check passes. This
   is the design in section 5.8.
5. **0009.** Scaffold with `--depends-on 0008_csv_download.md`. While declaring, the agent finds that
   background processing (Q2) changes where the control lives (Q1) and how progress is reported (Q3),
   and that it needs a job runner (B1). All four are coupled. The precheck reports
   `largest_coupled_cluster_size` 4 > 3 with members B1, Q1, Q2, Q3. The agent considers moving
   progress reporting into its own design, but Q3 changes the answer to Q1, so the split is not
   honest. It spends no retry on the budget. It writes the prose, renders (the box says **Within
   budget: no**), and checks (it passes, with one warning).
6. `terrastep build`, then `terrastep check`. Everything passes, with one warning.
7. The agent reports as in section 10.8.

### 10.10 Rules the model must never break

- Never create a design file by hand. Use `terrastep design scaffold`.
- Never write or edit `schema_version`, `policy_id`, or the Complexity box.
- Never put more than one design in a file.
- Never scaffold a design before its prerequisites pass `terrastep check`.
- Never make a design look within budget by deleting a real evaluation element, merging independent evaluation elements, leaving
  a choice or assumption in prose, relabeling a coupled edge as sequencing, or splitting coupled evaluation elements
  across designs.
- Never edit a validated prerequisite to suit a dependent. Make the coupled evaluation elements one design instead.
- Never edit `terrastep.toml` to make a design pass.
- Never claim a check that did not run.

### 10.11 Instruction block for the skill

`skilldoc.py` adds this text to `SKILL.md`, next to the existing procedure. It contains no limit
values, because limits belong to each repository.

> ## Writing design documents under a brain budget
>
> Use this procedure when you are asked to plan or design work and `terrastep design budget` reports
> `"enabled": true`. When it reports `false`, follow the design procedure above without the budget
> steps.
>
> 1. **Read the budget.** Run `terrastep design budget --format json`. Use its limits and
>    `max_retries`. Do not assume the defaults. Do not copy the limits into any file.
> 2. **Decompose before writing.** List every evaluation element: each consequential choice (another plausible
>    answer would change behavior, a public contract, persistent state, access control, or the
>    implementation approach; a recommended default still counts) and each assumption the reviewer
>    must judge. An evaluation element that must be settled or verified before work starts is a blocker; any other
>    is a question. For each pair of evaluation elements, ask: "If the first answer changed, would I have to
>    reconsider the second? What specific constraint would change?" Keep coupled evaluation elements in one design.
>    Split designs only where one design can rely on a stated contract from another. There is no
>    limit on the number of designs.
> 3. **Order the designs** so each comes after its prerequisites. A prerequisite must pass
>    `terrastep check` before you scaffold a design that depends on it.
> 4. **Scaffold** each design with `terrastep design scaffold`. Never create or overwrite a design
>    file by hand.
> 5. **Declare.** Read each prerequisite's file for its contract. Write the evaluation elements in Blockers and
>    Questions, each with a recommendation. In `brain_budget`, add the edges and a `contract` for each
>    `depends_on` entry. Use `sequencing` (supplier to consumer) only when the supplying answer can stay
>    fixed. Use `coupled` when the evaluation elements must be judged together, or when you are unsure. One record
>    per pair, direct constraints only. Never write `schema_version`, `policy_id`, or the Complexity
>    box.
> 6. **Precheck** with `terrastep design precheck FILE --format json` before you write prose. Fix what
>    it reports. If a measure is over budget and an honest re-split exists, try it. If the excess is a
>    coupled cluster, keep it together; the design will be flagged.
> 7. **Write the prose.** Replace every draft marker. Recommendations must mention every open evaluation element. If
>    writing reveals a new choice, assumption or dependency, make it an evaluation element or an edge and precheck
>    again.
> 8. **Render and check.** Run `terrastep design render FILE`, then
>    `terrastep check FILE --format json`. Patch only what the diagnostics name. Render again if a patch
>    changes a measure. Check again after the last edit.
> 9. **Respect `max_retries`.** A retry is one round of changes after a reported failure or an
>    over-budget measure. The count is per design, shared between precheck and check. When it runs
>    out, deliver the design: flagged if it is over budget, or as a failed draft if format failures
>    remain.
> 10. **Finish.** Run `terrastep build`, then `terrastep check`. Report each design in prerequisite
>     order, with whether it is within budget, which measure is over and what split you tried, and its
>     open blockers. Never claim a check that did not run.
>
> Never make a design look within budget by deleting a real evaluation element, merging independent evaluation elements, leaving a
> choice in prose, relabeling a coupled edge as sequencing, or splitting coupled evaluation elements across designs.

The skill's `description` also changes, so that a planning request loads the skill: "Use when writing,
reviewing, or checking a terrastep design document, when asked to plan or design work in a repository
with a terrastep.toml, or when a task mentions terrastep, scan_dirs, brain budget, or the
Blockers/Questions/Recommendations/Sequencing shape." Skill selection is a text match. So a consuming
repository should also add one line to its `CLAUDE.md`: "Plan and design work with the terrastep
skill."

---

## 11. Architecture in terrastep

### 11.1 Modules

| Module | Today | With brain budget |
|---|---|---|
| `config.py` | Loads `terrastep.toml`. Every key has a default. Unknown keys are ignored. | A frozen `BrainBudgetConfig` (`enabled`, `max_retries`, `limits`) and `BudgetLimits`. Strict validation of the two new tables. A `ConfigError` exception. New `CONFIG_HELP` entries. |
| `core.py` | Parser, design rules, index. Never writes. | `ROLE_ALIASES` gains `complexity`. `Doc` keeps the raw frontmatter text for the strict loader. `check_doc` calls `budget.check_layer` for design documents when brain budget is on. The note/legacy warning. `FAILURE_CODES` gains the `brain-budget-*` codes. `render_status` writes the `In budget` column, asking `budget.py` for each design's flag. |
| `budget.py` (new) | — | `FORMAT_DEFINITION`, `BASE_SCHEMA`, the identity functions, the strict YAML loader, the small schema validator, the edge, graph and prerequisite rules, the measures (using `core.parse_items`), the Complexity box as a text transform, and the scaffold text. **Never writes a file.** |
| `cli.py` | Argparse and dispatch. | The `design` verb with four actions. `--format json` for `check`. `ConfigError` → exit 2. Writes the output of scaffold and render, as `cmd_build` writes the index. |
| `hooks.py` | Pre-commit and "check if changed". | No change. It calls `core.check_docs`. |
| `skilldoc.py` | Generates `terrastep_101.md` and the skill. | Adds the procedure in section 10.11, a generated `skill/references/brain_budget.md` (measures, default limits, the working schema with the current `schema_version`, codes, edge rules), the configuration rows, and the new skill description. |
| `migrate.py` | Proposes frontmatter. | No change. |

`budget.py` is one module. terrastep's convention (0001) is to split a file only when a test or a change
gives a reason. It is separate from `core.py` because the layer has its own constants, and the existing
design rules in `core.py` stay unchanged.

### 11.2 How each verb flows

```text
terrastep check [FILES]
  config.load ──(ConfigError)──> exit 2
  core.scan_docs → core.check_docs
      per document: check_frontmatter → type design: check_body (unchanged)
                                         + budget.check_layer(doc, corpus, cfg, stage="final")
                                           when enabled and status is planning or ready
  cli prints text or JSON → exit 0 or 1

terrastep design precheck FILE
  config.load → core.scan_docs → budget.check_layer(doc, corpus, cfg, stage="declarations") → report

terrastep design render FILE
  config.load → read file → budget.render(text, cfg) → new text, or RenderRefused(reasons)
  cli writes the file only if the text changed

terrastep design scaffold ...
  config.load → core.scan_docs → core.next_id → prerequisite gate (check_docs on each target)
  → budget.scaffold_text(...) → cli writes the new file (refuses if it exists)
```

`corpus` is a filename-to-`Doc` index, built once per run.

### 11.3 The schema validator: no new runtime dependency

terrastep's runtime dependencies are `pyyaml` and `tomli` (Python < 3.11). Plan 0002, Q1, kept that
list. The `jsonschema` library brings `referencing`, `jsonschema-specifications`, `attrs` and the
compiled `rpds-py`.

The ledger schema uses only `type`, `properties`, `required`, `additionalProperties: false`, `items`,
`enum`, `const`, `pattern`, `minLength`, and local `$ref`. `budget.py` implements exactly that set. A
test fails if the schema ever uses another keyword. A conformance test runs every fixture through both
this validator and `jsonschema` (added only to the `dev` extra), and asserts the same result.

### 11.4 The strict YAML loader

`budget.py` composes the frontmatter with `yaml.compose` and walks the `brain_budget` node:

- A node reached twice is an alias. PyYAML reuses the anchored node object.
- A key with the merge tag is a merge.
- A mapping with a repeated key is a duplicate.
- A tag outside string, integer, float, boolean, null, sequence and mapping is not allowed. This also
  catches an implicit timestamp.

Then it constructs the value. The same node positions let `render` replace the stamps in place.

### 11.5 Hooks, skill, index, version

- **Hooks.** The pre-commit hook and the Stop hook call the same check, so they enforce the layer with
  no new code. An over-budget design only warns, so it can always be committed.
- **Skill.** `terrastep skill build` regenerates the skill and the new reference. The existing
  staleness test catches a change that was not regenerated. Consuming repositories run
  `terrastep skill install --force` after upgrading (`distribution.md`, section 3).
- **Index.** `render_status` adds the permanent `In budget` column (section 5.9). The output stays
  deterministic, with no timestamp, as today.
- **Version.** The layer is opt-in. The new `complexity` role can only remove a warning, never add a
  failure. No document's own check result changes. The new index column would make an existing user's
  `STATUS.md` stale, which `distribution.md` treats as a MAJOR change. But terrastep has not been
  distributed: the local repository is the only copy. So the release is 0.2.0, and the commit that adds
  the column also regenerates terrastep's own `STATUS.md` (OQ10). The version bump, `terrastep build`,
  and `terrastep skill build` go into one commit, as `CLAUDE.md` requires.

---

## 12. Integration decisions

These are the decisions for the terrastep design documents in section 17. Each gives the decision and
its reason.

- **I1. A layer on `type: design`. No new type.** A plan is a design. Notes and legacy documents are not
  budgeted: they carry no evaluation elements to judge. A warning covers a note or legacy document
  that has Blockers or Questions sections.
- **I2. terrastep's design format is unchanged.** The layer adds only the ledger and the Complexity box.
  The worked example passes terrastep 0.1.0's real check, with one warning that the `complexity` role
  removes.
- **I3. The section decides an evaluation element's type.** Blockers and questions are evaluation
  elements. They have no type field. `evaluative_count` counts every blocker and question, resolved or
  not, so a tag change never lowers the count.
- **I4. The ledger holds only stamps, edges and prerequisites.** Evaluation elements exist once, in
  the body, so there is no body-to-ledger matching rule. The edge field is `type`: a type is called a
  type.
- **I5. The budget is a flag.** `in_budget` appears in the Complexity box and in reports. It is a
  warning, never a failure. There is no gate, no `outcome`, and no escalation document.
- **I6. `max_retries` is the one setting for token spend.** It covers format fixes and re-split
  attempts. It is not spent on an irreducible coupled cluster.
- **I7. Limits for developers:** 10 / 11 / 3 / 2000. The cluster limit keeps what must be held at once
  small. The evaluative count allows a larger total.
- **I8. The format belongs to the code.** Only `enabled`, `max_retries` and the limits are configurable.
- **I9. Identity stamps are computed at load time**, and stored only in the frontmatter. Each is
  `sha256:` plus twelve hexadecimal characters (decided, OQ7).
- **I10. `schema_version` covers the layer's format definition.** terrastep's own design rules stay
  versioned by the terrastep version.
- **I11. A small built-in schema validator.** No runtime `jsonschema`.
- **I12. Strict YAML only inside `brain_budget`.**
- **I13. The final validation is `terrastep check`**, with `--format json` for every code.
- **I14. Exit codes:** 0 pass, 1 failure or refusal, 2 configuration or usage error.
- **I15. Opt-in:** `enabled = false` by default. The skill ships to every repository, so without opt-in
  an upgrade would change how agents write designs in repositories that never chose brain budget.
- **I16. Names follow the convention of where they appear.** `brain_budget` in TOML, YAML and
  Python. `brain-budget-` as the prefix of failure codes, which are kebab-case in terrastep (decided,
  OQ4). `bb-` is not used: a new reader cannot tell what it means.
- **I17. Scaffold enforces prerequisite order.** The prerequisite must pass `terrastep check`. Over
  budget is fine.
- **I18. The layer applies at `planning` and `ready` only.** Later statuses keep terrastep's rules, so
  tuning the limits never fails the repository's history.
- **I19. The verb group is `terrastep design`:** `budget`, `scaffold`, `precheck`, `render`. Scaffold
  also works with brain budget off.
- **I20. `render` adopts existing designs.** It adds the ledger and the Complexity box to a `planning`
  design that has neither.
- **I21. A Codex skill comes later.** The CLI and the rules do not depend on the agent.
- **I22. `STATUS.md` gets a permanent `In budget` column** (decided, OQ5). It shows `yes`, `no`, or
  `NA`, and it is present even when brain budget is off (section 5.9). The owner sees the harder
  designs before opening any of them.

---

## 13. Open questions for the owner

- **OQ1. `ready` runs the layer too?** Recommended: yes, so a design reaches approval current with the
  policy and format. Cost: after a limit change, each `ready` design needs `render` and `check` again.
- **OQ2. Approval order.** Warn when a design is `ready` or `in-progress` while one of its prerequisites
  is still `planning`? Recommended: a warning, not a failure.
- **OQ3. Failed drafts.** Leave them in `scan_dirs` (recommended: the hooks prevent a commit), or move
  them outside?
- **OQ4. The code prefix. Decided (2026-09-29):** `bb-` was confusing. Failure codes use
  `brain-budget-`; TOML, YAML and Python names use `brain_budget`, each by the convention of where it
  appears (I16).
- **OQ5. `STATUS.md`. Decided (2026-09-29):** `In budget` is a permanent index column, with `NA` when
  the budget is not active (I22, section 5.9). This raises OQ10.
- **OQ6. Codex.** When should `terrastep skill install` also write `.agents/skills/terrastep/`?
- **OQ7. Identity length. Decided (2026-09-29):** twelve hexadecimal characters (I9).
- **OQ8. Record retries?** With a soft budget, the number of retries used is evidence that the agent
  tried. Recommended: report it in the chat summary only, so `check` stays read-only.
- **OQ9. A verification section.** Should a budgeted design require a `verification` section? terrastep
  does not require one today. Recommended: no. The scaffold writes one, and the layer stays additive.
- **OQ10. The version number. Decided (2026-09-29): 0.2.0; the MAJOR rule has no effect yet.** The
  permanent `In budget` column changes the index format. Any repository that already uses terrastep
  would find its `STATUS.md` stale after upgrading, and `terrastep check` would fail `stale-index` until
  someone ran `terrastep build`. `distribution.md` asks for a MAJOR version bump for any change that can
  make an already-passing repository fail. That guidance is sound. But terrastep has not been
  distributed at all: it has no git remote, no PyPI release, and no installation in another
  repository. The local terrastep repository is the only copy in existence. So the only `STATUS.md`
  affected is terrastep's own, and the same commit that adds the column regenerates it. The rule
  applies from the first real distribution onward. After that, a change like this one needs the MAJOR
  bump.

---

## 14. Verification plan

The tests follow terrastep's existing patterns: a passing fixture, one mutation per rule that fails
with exactly the expected code, and generated-file staleness.

**Configuration**
- Defaults apply when `[brain_budget]` is missing. A partial `[brain_budget.limits]` changes only what
  it lists.
- An unknown key is rejected. Boolean, negative, and non-integer values are rejected. A configuration
  error exits 2.
- With `enabled = false`, every existing fixture gives exactly today's check result. The only change is
  the index column, which reads `NA`.

**The `In budget` column**
- The column is present with brain budget on and off, in all three index tables.
- `yes` and `no` for designs in `planning` and `ready`. `NA` for notes, legacy documents, later
  statuses, malformed designs, and every document when brain budget is off.
- Crossing a limit, or changing a limit in `terrastep.toml`, makes the index stale (`stale-index`)
  until `terrastep build` runs.
- `render_status` stays deterministic: two builds give identical bytes.

**Identity**
- Golden values: `sha256:4a30b1da8ac7` for the defaults, `sha256:cfd3b3f6f3d5` with
  `word_count = 2500`.
- Key order and whitespace do not change `policy_id`. Every limit change does.
- A change to any `FORMAT_DEFINITION` entry changes `schema_version`. The working schema's `const`
  equals the hash of the definition without it.

**Ledger and YAML**
- The supported-keyword guard. Conformance with `jsonschema` on every fixture.
- Inside `brain_budget`, each of these is rejected: a duplicate key, an alias, a merge key, a custom tag,
  and an unquoted date. The same constructs elsewhere keep today's result, and `status_changed` still
  parses as a date.
- An edge with `kind` fails. An edge to an evaluation element that is not in the body fails
  `brain-budget-edge`.
- Every new code starts with `brain-budget-`, and the `FAILURE_CODES` registry test passes.

**Measures and graph**
- `evaluative_count` counts resolved and open blockers, and questions, whether written as headings or
  as bold run-ins.
- Clusters: empty (0), isolated (1), chain Q1–Q2–Q3 (3), two disconnected clusters. A sequencing edge
  does not enlarge a cluster. A sequencing cycle across clusters is found.
- A prerequisite cycle across three designs is reported on each of them.
- The word count includes front sections and BQRS, and excludes the frontmatter, the Complexity box, and
  dated sections. The worked example counts 245.

**The flag**
- Over budget: a warning, exit 0, "Within budget: no" naming the measures and members. The pre-commit
  hook accepts it. `ready` is allowed.
- A format failure still fails, in or over budget.

**Render and scaffold**
- A second render gives identical bytes. Sibling keys, comments and quoting survive byte-for-byte.
- Render updates the stamps after a policy change. It adds a missing ledger and box. It refuses an
  invalid ledger or a missing `## Blockers`, and writes nothing then.
- Scaffold takes the next free number, refuses to overwrite, refuses a directory outside `scan_dirs`,
  and refuses a failing prerequisite. It accepts an over-budget one. With brain budget off, it writes
  a plain design skeleton.
- A fresh scaffold fails the final check until it is completed.

**Stages, statuses, integration**
- The precheck and the final check report the same three structural measures. The precheck reports
  `word_count`, `format_valid` and `in_budget` as `null`.
- The layer applies at `planning` and `ready` only. A policy change never fails `in-progress`,
  `implemented` or `closed` designs.
- A note with a Questions section warns. A note is never measured.
- The JSON output shape and the receipt hashes.
- The `FAILURE_CODES` registry test and the skill staleness test pass.
- terrastep's own journal (0001, 0002, both `implemented`) still passes with brain budget on.

---

## 15. Evaluation plan

The limits and the soft budget are hypotheses. A pilot on real requests records:

- **The flag hypothesis (section 2.8).** How often designs are `in_budget: false`. For each flagged
  design: was the excess an irreducible coupled cluster, or did the agent stop early? Compare the
  owner's review effort for flagged and unflagged designs. The hypothesis holds if flagged designs are
  rare, their extra effort is modest, and nobody misses an escalation process.
- **Token spend.** Retries per design, output tokens (including tool-call arguments), and time to a
  valid design. Is `max_retries = 2` the right spend?
- **Mechanical failures, by code.** Record them separately from over-budget flags.
- **Review effort.** The owner's active review time per design, and one rating right after each review
  on a nine-point mental-effort scale (1 very, very low to 9 very, very high; Appendix B, [10], [11]).
- **Declaration quality.** A sample audit for choices or assumptions left in prose, wrong coupling
  labels, and lost requirements.

Rules for the pilot:

- A higher in-budget rate that comes from under-declaring is a regression.
- Do not reward shorter output by itself.
- Change one limit at a time. `policy_id` groups the records by policy.
- Start with descriptive summaries. With fewer than about 50 designs, do not fit a model with more than
  two or three predictors chosen in advance.

---

## 16. What this proposal does not do

- It does not measure repository-derived boundaries or risk, or the size of the implementation diff.
- It does not prove that every choice and assumption became an evaluation element. The fresh-context
  audit is not built.
- It does not produce a feature map. The chat report and `depends_on` serve that purpose.
- It does not model approval. `ready` stays the owner's decision, in or over budget.
- It does not count retries with a tool (OQ8).
- It does not budget notes or legacy documents.
- It does not detect when a validated prerequisite changes under its dependents. A later extension
  could stamp each prerequisite's digest into `depends_on`, leaving out lifecycle keys.
- It does not add CI. The hooks enforce the rules locally.
- It does not ship a Codex skill yet.
- It does not migrate anything. `render` adopts a `planning` design on request (I20).

---

## 17. Suggested decomposition into terrastep design documents

These are `type: design` documents, listed in prerequisite order. Each uses a subset of sections 12
and 13 as its Blockers and Questions, and a subset of section 14 as its Verification. Once D ships,
terrastep can turn on brain budget in its own `terrastep.toml` and write its next change under the
budget.

| Doc | Scope | Decisions | Depends on |
|---|---|---|---|
| **A. Configuration and identity** | `[brain_budget]` parsing and validation. `ConfigError` and exit 2. `FORMAT_DEFINITION` and `BASE_SCHEMA` in `budget.py`. The identity functions. `terrastep design budget`. | I7, I8, I9, I10, I14, I15, I16 | — |
| **B. Declarations and precheck** | The strict YAML loader. The small schema validator and its conformance test. Evaluation elements through `core.parse_items`. Edge, graph and prerequisite rules. The three structural measures. `terrastep design precheck` and its JSON. The `brain-budget-*` codes. | I3, I4, I11, I12 | A |
| **C. Complexity box, render, scaffold, final check** | The `complexity` role. The word count. The box and the flag. `terrastep design render` (with adoption). `terrastep design scaffold` (with the ordering gate). The layer inside `terrastep check`, plus `--format json`. Status scope. Over-budget warnings. The note/legacy warning. The `In budget` index column. | I1, I2, I5, I13, I17, I18, I19, I20, I22; OQ1, OQ2, OQ3 | B |
| **D. Agent procedure and generated documents** | The skill procedure (section 10.11), `references/brain_budget.md`, the skill description, `terrastep_101.md`, the `CLAUDE.md` line. The 0.2.0 release (OQ10). Dogfooding. The pilot (section 15). | I6, I21; OQ6, OQ8, OQ9, OQ10 | C |

---

## Appendix A: Changes from v1 and from research note 4.2

### A.1 From proposal v1 (owner review, 2026-09-29)

| v1 | v2 | Reason |
|---|---|---|
| A new document type, `plan` | A layer on `type: design`; notes and legacy exempt | A plan is a design. Notes have no evaluation elements to judge. |
| Seven brain budget body sections | terrastep's design body, plus a Complexity box before Blockers | terrastep's format comes first. The two combine by addition. |
| A ledger listing decisions and unresolved items (`D`/`U` IDs, `kind`, `reopen_when`, `context`) | Evaluation elements live only in the body as `B`/`Q`. The ledger holds stamps, edges and prerequisites. | The section decides the type. Nothing is written twice. |
| `kind` on ledger records and edges | No type field on evaluation elements. The edge field is `type`. | A type is called a type. |
| `decision_count` and `unresolved_item_count` | `evaluative_count` | The same unit of review work. terrastep's blocker gate already covers the risk that unresolved items signaled. |
| Limits 3 / 2 / 6 / 3 / 600 | 10 / 11 / 3 / 2000 | Calibrated for developers. The cluster keeps what is held at once at 3. |
| `outcome`, `needs_design`, an escalation gate, design documents as the escalation venue | Removed. An `in_budget` flag in the Complexity box. | Owner hypothesis: a flag costs the reviewer less than an escalation process. |
| An over-budget failure (`bb-over-budget`) | A warning plus the flag | A soft budget. Format stays hard. |
| `max_repair_attempts` | `max_retries`, covering fixes and re-splits | One setting for token spend. |
| `bb-gate-blocking`, `bb-disabled`, `bb-id-dup`, `bb-body`, `bb-body-empty`, `bb-body-ledger` | terrastep's existing rules (`gate-open-blocker`, `body-*`) | Those rules already exist. |
| `bb-table` | `brain-budget-complexity` | The box now holds the flag and has a fixed place. |
| The `bb-` code prefix | `brain-budget-` for failure codes; `brain_budget` in TOML, YAML and Python | `bb` was confusing. Each name follows the convention of where it appears. |
| "Item" for a blocker or question | "Evaluation element" | "Item" is too vague. The schema's `item_id` became `element_id`. |
| No index change | A permanent `In budget` column in `STATUS.md`, `NA` when the budget is not active | The owner sees the harder designs before opening any of them. |
| Identity length left open | Twelve hexadecimal characters | Decided by the owner. |
| Version number left open (OQ10) | 0.2.0 | terrastep has not been distributed, so the MAJOR rule in `distribution.md` has no effect yet. |
| `terrastep plan …` verbs | `terrastep design …` | There is no plan type. |
| Scaffold required a prerequisite with `outcome: plan` | The prerequisite passes `terrastep check` | There is no outcome field. |
| Word count from the H1 to the Complexity section | From the H1 to the end of Sequencing, without the box | The body order changed. |

### A.2 From research note 4.2 (still true in v2)

| Note 4.2 | v2 | Reason |
|---|---|---|
| `.brainbduget.json` and the `brainbudget` key | A `[brain_budget]` table in `terrastep.toml`, and the `brain_budget` key | terrastep has one configuration file. One spelling. |
| Configurable document, frontmatter and schema settings | Code-owned constants | The generated skill cannot reflect per-repository format settings. |
| Identifiers written into the configuration by `config build` | Computed at load time; stored only in the frontmatter | A computed value cannot go stale. The TOML libraries in use can only read. |
| `schema_version` hashes the schema only | It hashes the whole layer format definition | A counting change re-scores documents. |
| `P1` plan IDs, `plan.id`, `plan.title` | The terrastep number and H1 | terrastep numbering already exists. |
| `depends_on` with relative paths and `plan_id` | A bare filename resolved against the scanned documents | The same resolution as `blocked_by`. |
| An optional linked-file check | Always checked | terrastep always loads the whole corpus. |
| A separate checker CLI | `terrastep check` | One validator for the hooks and the agent. |
| Upper-case diagnostic codes | terrastep-style codes in `FAILURE_CODES` | terrastep's convention and registry test. |
| Claude Code and Codex skills; required CI | Claude Code now; Codex and CI later | What terrastep ships today. |

---

## Appendix B: References

1. Microsoft Research. "To Copilot and Beyond: 22 AI Systems Developers Want Built."
   https://www.microsoft.com/en-us/research/publication/to-copilot-and-beyond-22-ai-systems-developers-want-built/
2. Sweller, J. "Element Interactivity and Intrinsic, Extraneous, and Germane Cognitive Load."
   *Educational Psychology Review*. https://doi.org/10.1007/s10648-010-9128-5
3. Cowan, N. "The magical number 4 in short-term memory: A reconsideration of mental storage
   capacity." *Behavioral and Brain Sciences*.
   https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/magical-number-4-in-shortterm-memory-a-reconsideration-of-mental-storage-capacity/44023F1147D4A1D44BDC0AD226838496
4. "A Cognitive Load Theory Approach to Defining and Measuring Task Complexity Through Element
   Interactivity." *Educational Psychology Review*. https://doi.org/10.1007/s10648-023-09782-w
5. Google engineering practices. "Small CLs."
   https://google.github.io/eng-practices/review/developer/small-cls.html
6. Nielsen Norman Group. "Progressive Disclosure." https://www.nngroup.com/articles/progressive-disclosure/
7. Fowler, M. "Architecture Decision Record."
   https://martinfowler.com/bliki/ArchitectureDecisionRecord.html
8. "Human oversight of agentic systems in practice: Examining the oversight work, challenges, and
   heuristics of developers using software agents." https://arxiv.org/abs/2606.05391
9. Microsoft Research. "You Shall Not Pass! Where and Why Developers Draw the Line on AI Autonomy."
   https://www.microsoft.com/en-us/research/publication/you-shall-not-pass-where-and-why-developers-draw-the-line-on-ai-autonomy/
10. Paas, F. (1992). Training strategies for attaining transfer of problem-solving skill.
    https://research.utwente.nl/en/publications/training-strategies-for-attaining-transfer-of-problem-solving-ski-2/
11. Paas, F., Van Merriënboer, J., and Adam, J. (1994). Measurement of cognitive load in instructional
    research. https://ris.utwente.nl/ws/files/248299579/Paas1994measurement.pdf
12. JSON Schema, draft 2020-12. https://json-schema.org/draft/2020-12/schema
13. Claude Code skills documentation. https://code.claude.com/docs/en/skills
