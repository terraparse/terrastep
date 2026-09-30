---
status: implemented
status_changed: 2026-09-29
type: design
next: None. Sequencing steps 1-8 are done (see "What was built" below). 0006 depends on this.
---

# Brain budget C: Complexity box, render, scaffold and the final check

## Summary

This is the third of four brain budget designs (the proposal,
`journal/origin/brain_budget_proposal_v2.md`, section 17, doc C). It depends on 0004 for
`budget.check_layer`, the three structural measures, `Doc.fm_text` and `Doc.fm_offset`. 0006
depends on it for the complete verb set that the skill procedure teaches.

This design makes brain budget visible and enforced. It adds the `complexity` role, the word
count, the Complexity box, `terrastep design render` and `terrastep design scaffold`, the layer
inside `terrastep check` with `--format json`, and the permanent `In budget` column in
`STATUS.md`.

**By the proposal's own measure this design is over budget.** It has 12 evaluation elements, and
the proposed limit is 10. Section 17 of the proposal groups them this way. An honest split
exists: scaffold and the index column (Q5, Q9, Q12) rely on the final check only through a
stated contract ("a design passes `terrastep check`" and "`in_budget` for a design"). The owner
decided on 2026-09-29 to keep this as one design, flagged.

## Scope

In scope:

- The `complexity` role in `core.ROLE_ALIASES` (proposal 5.5).
- `word_count` (proposal 4.5) and the Complexity box (proposal 5.6).
- `terrastep design render` (proposal 9.5) and `terrastep design scaffold` (proposal 9.3).
- The layer in `core.check_doc` at the final stage: rules 9 and 10 of proposal section 7.2, the
  status scope (7.5), and over-budget warnings (7.6).
- `terrastep check --format json` (proposal 7.8).
- The warning for a `note` or `legacy` document that has Blockers or Questions (proposal 5.1).
- The `In budget` column (proposal 5.9).

Not in scope: the skill procedure, the generated reference, the version bump and the pilot
(0006).

## The design

### The Complexity box and the word count

`ROLE_ALIASES` gains `"complexity": (r"complexity",)`. This removes today's "unclassified front
sections" warning for the heading. It adds no failure: the worked example passes terrastep
0.1.0's check today, with that one warning (checked 2026-09-29).

`budget.word_count(doc)` splits the raw Markdown on whitespace, from the H1 line to the end of
`## Sequencing`, without the whole Complexity section. It gives 245 on the worked example
(recomputed 2026-09-29). The box does not count its own words, so rendering it cannot change the
count.

`budget.complexity_box(measures, limits, members) -> str` returns the exact text of proposal
5.6. `check_layer(..., stage="final")` adds rule 9 for the whole file and rule 10: the box is
present, is the last front section, sits just before `## Blockers`, and equals what
`complexity_box` returns now (`brain-budget-complexity`).

### The final check

`core.check_doc` calls `budget.check_layer(doc, corpus, cfg, "final")` for a `type: design`
document when brain budget is on and the status is `planning` or `ready`. `check_docs` builds
`corpus` once per run. A measure over its limit adds a warning such as
`over budget: largest coupled cluster size 4 > 3 (B1, Q1, Q2, Q3)`. It never adds a failure.

`cli.cmd_check` and `hooks.check_snapshot` repeat the same stale-index logic today. This design
moves it into one function, `core.check_corpus(root, docs, cfg, only)`, which both call. The
JSON report and the pre-commit hook then read the same results.

`terrastep check --format json` prints the report in proposal section 7.8. Each budgeted design
has a `brain_budget` block. `corpus` holds `stale-index` and the in-progress cap warning.

With `--if-changed` and no uncommitted change in `scan_dirs`, text output stays as today: nothing,
exit 0. JSON output prints `{"ok": true, "skipped": true}` and exits 0, so a caller that parses
stdout always gets a JSON document. Every full report also carries `"skipped": false`. Decided by
the owner on 2026-09-29.

### `terrastep design render FILE`

`budget.render(text, cfg) -> str`, or it raises `RenderRefused(reasons)`. `cli.py` writes the
file only when the text changed.

1. It refuses when brain budget is off, the frontmatter does not parse, the ledger fails the
   YAML rules or the schema (stamp values ignored), `## Blockers` is missing, or a code fence is
   open.
2. It replaces the two stamp values in place, at the node marks from `yaml.compose` plus
   `Doc.fm_offset`. Every other byte of the frontmatter stays the same.
3. If there is no ledger, it appends one with the current stamps and empty `depends_on` and
   `edges`. This is how an existing `planning` design joins the budget.
4. It writes the box, or inserts it just before `## Blockers`.
5. It writes honest values, including an over-budget flag. A second run gives identical bytes and
   prints "unchanged".

### `terrastep design scaffold`

`terrastep design scaffold --title T [--slug S] [--dir D] [--depends-on FILE ...]` follows
proposal section 9.3. It takes the number from `core.next_id`, requires `--dir` inside a
`scan_dirs` entry, serializes the frontmatter with PyYAML, and never overwrites.

The prerequisite gate runs `core.check_doc` on each `--depends-on` target, with the whole corpus
as context. A target passes when that per-document check has no failure. The corpus-level
`stale-index` result does not count, because the agent runs `terrastep build` only at the end
(proposal 10.8). An over-budget target passes.

With brain budget off, scaffold writes the plain design skeleton, with no ledger and no
Complexity section.

### The `design` verb's actions

0003 added `design budget` and 0004 added `design precheck`. The four actions take different
arguments, so `design` uses nested subparsers, not a positional choice as `migrate` and `skill`
do. `skilldoc._verb_help` reads only the top-level subparsers today. This design extends it to
list the nested actions and their flags, so the generated `verbs.md` shows them.

### The `In budget` column

`render_status` writes an `In budget` column after `Status` in all three tables, whether brain
budget is on or off. It calls `budget.in_budget_value(doc, corpus, cfg) -> "yes" | "no" | "NA"`.

- The value comes from the recomputed measures, not from the box that was last rendered.
- `NA` when brain budget is off, the document is not a design, its status is `in-progress`,
  `implemented` or `closed`, or a measure is `None` (the ledger did not load).
- A design that fails another rule, such as `body-r-cover`, still gets `yes` or `no`, because
  its measures exist.

`render_status` gains a `corpus` argument, and `cmd_build` and `check_corpus` pass it.
terrastep's own `STATUS.md` is regenerated in the same commit.

## Verification

From proposal section 14, "The `In budget` column", "The flag", "Render and scaffold" and
"Stages, statuses, integration":

- Render twice gives identical bytes. Sibling keys, comments and quoting survive. Render
  re-stamps after a policy change, adopts a design with no ledger, and refuses (and writes
  nothing) on an invalid ledger or a missing `## Blockers`.
- Scaffold takes the next number, refuses to overwrite, refuses a `--dir` outside `scan_dirs`,
  refuses a failing prerequisite, and accepts an over-budget one. A fresh scaffold fails
  `terrastep check` until it is completed. With brain budget off, it writes a plain skeleton.
- The precheck and the final check report the same three structural measures on one file.
- Over budget: a warning, exit 0, "Within budget: no" with the measures and members. The
  pre-commit hook accepts it. `ready` is allowed.
- A policy change never fails an `in-progress`, `implemented` or `closed` design.
- A note with a Questions section warns. It is never measured.
- The column is present with brain budget on and off. `yes`, `no` and `NA` as above. Crossing a
  limit makes the index stale. Two builds give identical bytes.
- The JSON report's shape, and its receipt hashes.
- `check --if-changed --format json` with no change prints exactly `{"ok": true, "skipped": true}`
  and exits 0. With `--if-changed` and text output, it still prints nothing.
- `cmd_check` and `hooks.check_snapshot` give identical results on every fixture.
- `skilldoc` lists `design budget`, `precheck`, `render` and `scaffold` with their flags.
- terrastep's own journal passes with brain budget on.

## Blockers

None. The format facts this design relies on were checked against terrastep 0.1.0 on
2026-09-29: the worked example passes, and its word count is 245.

## Questions

### Q1 — Is brain budget a new document type or a layer?

**Recommendation:** a layer on `type: design`, with no new type (I1). Notes and legacy
documents are not measured. A note or legacy document with Blockers or Questions warns.

### Q2 — Does the layer change terrastep's design format?

**Recommendation:** no (I2). It adds only the ledger and the Complexity box. The `complexity`
role removes a warning and adds no failure.

### Q3 — Is being over budget a failure?

**Recommendation:** no, it is a flag (I5). It appears in the box, the reports and the index, and
as a warning. There is no gate, no `outcome` field and no escalation document. Format rules stay
hard.

### Q4 — What is the final validation?

**Recommendation:** `terrastep check`, with `--format json` for every code (I13). No separate
check verb, so the hooks and the agent run one validator.

### Q5 — Does scaffold enforce prerequisite order?

**Recommendation:** yes (I17). Each `--depends-on` target must pass its per-document check.
Over budget is fine.

### Q6 — At which statuses does the layer apply?

**Recommendation:** `planning` and `ready` only (I18), so tuning the limits never fails the
repository's history.

### Q7 — What is the verb group?

**Recommendation:** `terrastep design` with `budget`, `scaffold`, `precheck` and `render`
(I19), as nested subparsers. Scaffold also works with brain budget off.

### Q8 — How does an existing design join the budget?

**Recommendation:** `render` adds the ledger and the Complexity box to a `planning` design that
has neither (I20). Nothing migrates automatically.

### Q9 — Does `STATUS.md` show the flag?

**Recommendation:** yes, a permanent `In budget` column with `yes`, `no` or `NA`, present even
when brain budget is off (I22). The owner decided this on 2026-09-29 (OQ5).

### Q10 — Does the layer also run at `ready`?

The cost: after a limit change, each `ready` design needs `render` and `check` again (OQ1).

**Recommendation:** yes, so a design reaches approval current with the policy and the format.

### Q11 — Warn when a design is approved before its prerequisites?

The case: a design is `ready` or `in-progress` while a `depends_on` target is still `planning`
(OQ2).

**Recommendation:** a warning, not a failure.

### Q12 — Where do failed drafts stay?

A failed draft still has format failures after its retries (OQ3).

**Recommendation:** leave it in `scan_dirs`. The pre-commit hook stops it from being committed.

## Recommendations

1. Build brain budget as a layer on `type: design`, with the note and legacy warning (Q1).
2. Keep terrastep's design format unchanged except for the ledger and the box (Q2).
3. Report over budget as a flag and a warning, never a failure (Q3).
4. Make `terrastep check` the final validation, with `--format json` (Q4).
5. Gate scaffold on each prerequisite's per-document check (Q5).
6. Apply the layer at `planning` and `ready` only (Q6).
7. Group the actions under `terrastep design` as nested subparsers (Q7).
8. Let `render` adopt existing `planning` designs (Q8).
9. Add the permanent `In budget` column (Q9).
10. Run the layer at `ready` too (Q10).
11. Warn when a design is approved before its prerequisites (Q11).
12. Keep failed drafts in `scan_dirs` (Q12).

## Sequencing

1. `core.check_corpus`, used by `cmd_check` and `hooks.check_snapshot`. No behavior change.
2. The `complexity` role, `word_count`, `complexity_box`, and rules 9 and 10 at the final stage.
3. The layer in `check_doc`, status scope, over-budget warnings, the note and legacy warning,
   the prerequisite-order warning (Q11), and `brain-budget-complexity` in `FAILURE_CODES`.
4. `terrastep check --format json`.
5. `terrastep design render`.
6. `terrastep design scaffold`, and nested actions in `skilldoc._verb_help`.
7. The `In budget` column. Run `terrastep build` on this repository.
8. Run `terrastep skill build`, the full suite and `terrastep check`. Commit.

## What was built (2026-09-29)

Steps 1-8 done, each as recommended, no scope changes.

- **`core.py`**: the `complexity` role (found, by testing render end to end, that omitting it makes
  render silently insert a *second* box next to the first, since nothing recognized the existing
  one — this is exactly the "unclassified front section" case the design already names, so its
  fix was already in scope, just easy to skip by accident). `check_doc` gained a `corpus`
  parameter and now calls `budget.check_layer(doc, corpus, config, stage="final")` for a
  `planning`/`ready` design when brain budget is enabled — a local import inside the function
  (`from . import budget`), since `budget.py` already imports `core.py`; Python resolves the name
  when the function runs, not when the module loads, so the cycle never actually executes.
  `check_doc` also warns on a `note`/`legacy` document with a Blockers or Questions section, gated
  on `enabled` so a repository that never turned brain budget on sees no new warning (matching the
  proposal's own "the one visible change is the index column" claim). `check_corpus(root, docs,
  config, only)` unifies `check_docs` plus the stale-index comparison; `cli.cmd_check` and
  `hooks.check_snapshot` both call it now, so they cannot drift. `render_status` gained an
  optional `corpus` argument and writes the permanent `In budget` column.
- **`budget.py`**: `word_count` (reassembled from `doc.sections`, not re-parsed text, since a word
  count doesn't need exact spacing); `complexity_box` (matches the proposal's literal text,
  character for character, both within- and over-budget); `check_layer` extended to a `stage`
  parameter of `"declarations"` or `"final"`, sharing rules 1-9 and adding rule 10 (the box) and
  `word_count` only at `"final"`; `render` (the strict pre-check reuses 0004's schema validator
  with `schema_version` relaxed to a shape check, since render's whole job is to fix a stale one);
  `scaffold_text`/`default_slug`; `in_budget_value`; `check_report` (the full `--format json`
  shape).
- **`terrastep design render FILE`**: refuses and writes nothing on 7 distinct conditions (brain
  budget off, no frontmatter, unparseable frontmatter, an open code fence, `## Blockers` missing,
  a strict-YAML ledger problem, a schema problem); otherwise idempotent, confirmed on the
  proposal's own worked example (already-correct input reproduced byte-for-byte) and on a design
  scaffolded from nothing.
- **`terrastep design scaffold`**: gates each `--depends-on` on that target's own per-document
  check (an over-budget target passes; a failing one is refused by name and reason); `--dir` must
  resolve inside a `scan_dirs` entry; never overwrites. With brain budget off, writes a plain
  skeleton with no ledger and no Complexity section.
- **`terrastep check --format json`**, and `--if-changed --format json` with no change now prints
  exactly `{"ok": true, "skipped": true}` (text output is unchanged: silent, exit 0).
- **A real bug found and fixed while testing render, not while writing it**: the first render of a
  design that never had a `## Complexity` heading inserted the box with two trailing blank lines;
  a second render (now finding the box and replacing it) used one. Rendering twice therefore
  produced different bytes — caught by an idempotency test built specifically to model that exact
  "adopt a pre-brain-budget design" case, not by reasoning about the code.
- **Verified end to end in a scratch repository**, not only in `pytest`: scaffold a design, precheck
  it while it still has draft markers (fails, as designed), fill it in, precheck (passes), render,
  build, check (passes) — matching proposal 10.5's whole per-design loop by hand.
- **Two decisions not spelled out in the design text**:
  - `corpus` for `render`'s own internal measure computation is the single document being
    rendered (`{doc.name: doc}`), not the whole repository — a lone `render` call cannot see other
    documents' `depends_on` graphs, so a prerequisite-cycle involving other files is only ever
    caught by `terrastep check` afterward, which does load the whole corpus.
  - The note/legacy warning and the brain-budget layer's internal `warnings` field are both gated
    on `[brain_budget] enabled`, inferred from the proposal's own claim that disabling brain budget
    leaves every existing behavior unchanged except the index column.
- **Tests**: `tests/test_budget.py` gained 22 (word count, the box's exact text, render's
  idempotency/refusals/adoption/byte-preservation, scaffold_text, `in_budget_value`);
  `tests/test_cli.py` gained 13 (render, scaffold's every refusal and success path, `check
  --format json`, the `--if-changed` skip, the note warning, the `In budget` column, a
  stale-index-on-limit-change round trip, `cmd_check`/`hooks.check_snapshot` agreement, and that
  brain budget on never re-fails this repository's own already-shipped designs). Full suite: 217
  passing (181 before this design).

No divergence from the plan as written, beyond the two decisions above and the box-insertion bug
fix. `enabled = false` is still this repository's setting; 0006 turns it on.
