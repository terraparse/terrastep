---
status: implemented
status_changed: 2026-09-29
type: plan
next: None. Sequencing steps 1-7 are done (see "What was built" below).
brain_budget:
  schema_version: sha256:6c16c11afcf0
  policy_id: sha256:4a30b1da8ac7
  depends_on: []
  edges:
    - from: Q1
      to: Q2
      type: sequencing
      contract: Q1 fixes the exact replacement word ("plan"). Q2 only asks whether that specific word collides with migrate.py's existing is_plan/plan_dir concept.
    - from: Q1
      to: Q3
      type: sequencing
      contract: Q1 fixes the exact replacement word. Q3 only asks how existing documents adopt that fixed word.
    - from: Q1
      to: Q4
      type: sequencing
      contract: Q1 fixes the exact replacement word. Q4 only notes that PLAN_TYPES, named before this proposal existed, already matches it.
    - from: Q1
      to: Q7
      type: sequencing
      contract: Q1 fixes the exact replacement word. Q7 only checks which other same-spelled things are, and are not, affected by that specific word.
---
# Rename type: design to type: plan, and the design verb group to plan

## Summary

This design renames terrastep's `type: design` value to `type: plan`, and the `terrastep design`
CLI verb group to `terrastep plan`, everywhere both are load-bearing: the format's own
`TYPES`/`PLAN_TYPES` list, the CLI, the generated docs and skill, and the frontmatter of every
document in `journal/plans/`. It does not bump the version. This is the first design written
under terrastep's own brain budget (0003-0006).

The owner's reasoning: terrastep is pre-public, with no installation outside this repository. A
breaking rename that would need a MAJOR version bump and a migration note after real distribution
costs nothing today. "Plan" also matches `journal/plans/`, the directory every one of these
documents already lives in, and reads as a concrete build plan rather than an open-ended
exploration — the same distinction Appendix A of the brain budget proposal drew when it rejected
a separate `type: plan` in favor of folding "plan" into "design" (`brain_budget_proposal_v2.md`,
Appendix A: "A plan is a design"). This design does not relitigate that reasoning; it changes
which of the two words the format uses for the same concept, for an unrelated reason (word choice
for a pre-public project), not because the concept split in two.

## Scope

In scope:

- `core.py`: `TYPES`/`PLAN_TYPES`'s value (`"design"` → `"plan"`; the `PLAN_TYPES` *name* is
  unchanged — see Q4), `ROLE_ALIASES`'s `design` role is unchanged (see Q7), every failure-code
  message and docstring that says "design document".
- `cli.py`: the `design` verb group becomes `plan` (`terrastep plan budget|precheck|render|scaffold`),
  and every identifier and printed message under it.
- `budget.py`: every docstring, message, and generated-text string that says "design"/"design
  document".
- `config.py` / `migrate.py`: the pre-existing `is_plan`/`[migrate] plan_dir` naming, which
  already used the word "plan" for an unrelated concept before this design existed (see Q2).
- The frontmatter `type:` field of every document in `journal/plans/` (0001-0007): `design` → `plan`.
- The generated docs and skill (`terrastep skill build`), `readme.md`, and the test suite.

Not in scope: a version bump (Q5); a backward-compatible `design` alias (Q6); the body prose of
already-`implemented` documents (0001-0006), which stays as originally written — a historical
record, not living documentation (Q3); `journal/origin/**` and `journal/misc/**`, which this
repository already treats as inherited, unedited history; the `brain-budget-*` failure code
prefix, which names the layer, not the document type (Q7); the Stop hook shim
(`integrations/claude/stop_hook.sh`), which calls `terrastep check`, never `terrastep design`.

## The design

### What changes, mechanically

1. **The type value.** `core.PLAN_TYPES = ("plan",)` (was `("design",)`). `TYPES = PLAN_TYPES +
   ("legacy", "note")` is unchanged in shape. Every document whose frontmatter still says
   `type: design` now fails `fm-type`, which is exactly how the existing checker already reports
   an unrecognized type — no new failure code is needed.
2. **The verb group.** `cli.py`'s `design` subparser, its nested actions, and every function and
   local name under it (`cmd_design_budget` → `cmd_plan_budget`, `design_sub` → `plan_sub`, the
   `design_action` dest → `plan_action`, and so on) are renamed to `plan`. The four actions
   (`budget`, `precheck`, `render`, `scaffold`) and their flags keep their own names — only the
   group name changes.
3. **Everywhere else "design" names this concept.** `budget.py`'s docstrings and user-facing
   strings (for example `check_layer`'s comments, `scaffold_text`'s doc, `precheck_report`'s
   field names that are prose, not schema, such as the `"Read the design document"`-style
   messages) are reworded to "plan"/"plan document". Generated prose in `skilldoc.py`
   (`SKILL_PROCEDURE`, the brain-budget procedure section added in 0006, `references/*.md`) is
   reworded the same way; regenerating picks it all up in one pass.
4. **The existing corpus.** 0001 through 0007's frontmatter `type:` field becomes `plan`. Their
   body prose is untouched — see Q3.
5. **`migrate.py`'s pre-existing collision.** `is_plan` and `[migrate] plan_dir` predate this
   design and mean "looks like a real planning document" (mapped to `type: legacy`, never to
   `type: design`). Once `plan` is a real type value, that naming would mislead a reader into
   thinking `is_plan` implies `type: plan`. Both are renamed — see Q2.

### What does not change

- terrastep's document *shape* (frontmatter keys, the four decision sections, item tags,
  recommendation coverage) is exactly as it was. This is a name change to one enum value and one
  verb group, not a format change.
- The brain budget ledger's own shape (`schema_version`, `policy_id`, `depends_on`, `edges`) is
  unaffected; `budget.schema_version()`'s hash does not change, because `FORMAT_DEFINITION`
  itself names no document type.
- `ROLE_ALIASES["design"]` (the front-section role matched by headings like `## Design`,
  `## Solution`, `## Proposal`) stays. It is a different, existing concept: the part of *any*
  document — a plan, and before this design, a design — that describes the shape of the
  solution. A plan still has a design section; that is ordinary English, not the type value.

## Verification

- `core.TYPES == ("plan", "legacy", "note")`. A fixture with `type: design` now fails `fm-type`;
  the same fixture with `type: plan` passes exactly as `type: design` did before.
- `terrastep plan budget|precheck|render|scaffold` all work; `terrastep design ...` is gone
  entirely (Q6: no alias).
- Every one of 0001-0007's frontmatter reads `type: plan`. `terrastep check` passes on this
  repository with brain budget on.
- `grep -rn '"design"' src/terrastep/*.py` returns nothing except the unrelated
  `ROLE_ALIASES["design"]` role entries (Q7).
- The skill staleness test passes after `terrastep skill build`; `SKILL.md`'s procedure and
  `references/*.md` say "plan", not "design", throughout.
- `terrastep.__version__` is unchanged at `0.2.0` (Q5).
- The full test suite passes; `tests/fixtures/0051_design_ok.md`'s frontmatter (and any test
  asserting on the string `"design"` as a type or verb) is updated to `plan`.

## Complexity

**Within budget: yes.**

| Measure | Actual | Limit |
| --- | ---: | ---: |
| Evaluative count | 7 | 10 |
| Dependency edge count | 4 | 11 |
| Largest coupled cluster size | 1 | 3 |
| Word count | 1667 | 2000 |

## Blockers

None. Every choice here is the owner's to accept or change, not a fact this design must verify
before work starts. The one external fact this design rests on — that terrastep has no
installation outside this repository — was stated by the owner, not discovered by terrastep.

## Questions

### Q1 — What is the exact new vocabulary?

**Recommendation:** the type value `design` → `plan`; the CLI verb group `design` → `plan`
(`terrastep plan budget|precheck|render|scaffold`); every Python identifier under it
(`cmd_design_*` → `cmd_plan_*`, `design_sub` → `plan_sub`, the `design_action` dest →
`plan_action`); the prose noun "design document" → "plan document". Keep "planning documents" —
the existing umbrella term for every scanned file, of any type — unchanged; it already reads as
distinct from "plan document" (one specific type) in ordinary English, and renaming the umbrella
term is not asked for.

### Q2 — `migrate.py` already uses "plan" for something else. Does that collide?

`config.migrate.plan_dir` and the local `is_plan` (`migrate.py`) predate this design. They mean
"has the shape of a real planning document" and currently map such a document to `type: legacy`
— never to `type: design`. Once `plan` becomes a real type value, a reader could mistake
`is_plan` for "becomes `type: plan`"; it would still mean `type: legacy`.

**Recommendation:** rename `is_plan` to `is_substantive`, and the config key `[migrate] plan_dir`
to `[migrate] legacy_dir` (matching what it actually selects: documents that default to `type:
legacy`). Cheap now; the config key has no known external readers.

### Q3 — Do already-`implemented` documents' frontmatter and body prose both change?

**Recommendation:** the frontmatter `type:` field, yes — mechanically, on every document,
because `core.TYPES` will no longer recognize `design` at all, so a document left unrewritten
would immediately fail `fm-type`. The body prose, no — 0001 through 0006 describe the mechanism
and vocabulary that existed when each was implemented, the same way 0001 still describes a
`seed/scripts/` layout that no longer exists. Rewriting old prose to match a later rename would
misrepresent when each decision was actually made.

### Q4 — `core.PLAN_TYPES` is already named after this design's new word. Rename it too?

**Recommendation:** no. `PLAN_TYPES` currently holds `("design",)` — a name that was, until now,
coincidental. After this design, it holds `("plan",)`, and the name stops being coincidental and
starts being accurate. Nothing here is a problem to fix.

### Q5 — Version bump?

**Recommendation:** none. The owner decided this directly: terrastep has no installation outside
this repository, so `distribution.md`'s MAJOR-bump rule — written for a change that could fail an
already-passing external repository — does not yet apply, exactly as 0006 reasoned for the
`In budget` column. `terrastep.__version__` stays `0.2.0`.

### Q6 — Does `terrastep design` stay as a deprecated alias during a transition?

**Recommendation:** no alias. There is no known external caller to protect, and keeping one
would recreate, on purpose, the exact path-dependency this design exists to avoid while it is
still free to avoid.

### Q7 — What, despite sharing the word, is explicitly *not* renamed?

**Recommendation:** three things, each a genuinely different concept that happens to share a
spelling: (1) `ROLE_ALIASES["design"]`, the front-section role matched by headings like
`## Design`/`## Solution`/`## Proposal` — a plan's own design section, unrelated to the type
value. (2) The `brain-budget-*` failure-code prefix and `FORMAT_DEFINITION` — they name the
brain budget *layer*, not the document type; nothing about them mentions `design` or `plan` at
all. (3) `journal/origin/**` and `journal/misc/**` — this repository's existing convention already
treats these as inherited or historical notes, never rewritten for a later change.

## Recommendations

1. New vocabulary as in Q1; apply it in one coordinated pass across `core.py`, `cli.py`,
   `budget.py`, `skilldoc.py`, generated docs, `readme.md`, and the tests.
2. Rename `is_plan` → `is_substantive` and `[migrate] plan_dir` → `[migrate] legacy_dir` (Q2).
3. Rewrite every document's frontmatter `type:` field; leave body prose of implemented documents
   untouched (Q3).
4. Keep the name `PLAN_TYPES` (Q4).
5. No version bump (Q5).
6. No `design` alias (Q6).
7. Leave the three things in Q7 alone.

## Sequencing

1. `core.py`: `PLAN_TYPES`'s value, failure-code messages, docstrings. `ROLE_ALIASES` untouched.
2. `cli.py`: rename the verb group, every function/local name under it, and every printed
   message. `budget.py`: every docstring and user-facing string.
3. `config.py`/`migrate.py`: `is_plan` → `is_substantive`, `plan_dir` → `legacy_dir`, and the
   matching `CONFIG_HELP` text.
4. Rewrite 0001-0007's frontmatter `type:` field to `plan`. Leave 0001-0006's body prose as
   written.
5. `terrastep skill build`, `terrastep skill install --root . --force`, `terrastep build`.
6. Update `readme.md` and the test suite (fixtures, CLI invocations, assertions) to match.
7. Run the full test suite and `terrastep check`. Precheck, render, and check this design itself
   under the budget before it ships. Commit.

## What was built (2026-09-29)

Steps 1-7 done, each as recommended, no scope changes.

- **`core.py`**: `PLAN_TYPES = ("plan",)`. `REQUIRED_ROLES`/`EXPECTED_ROLES` are now keyed by
  `"plan"` — a real bug caught before it shipped: these dicts are looked up as
  `REQUIRED_ROLES[doc.type]`, so leaving the key as `"design"` would have raised `KeyError` on
  every plan document the moment `doc.type` became `"plan"`. `EXPECTED_ROLES["plan"]`'s *value*,
  `("design", "scope")`, keeps its `"design"` entry unchanged — that names the front-section
  role (`## Design`/`## Solution`), a different thing from the dict's own key (Q7).
  `ROLE_ALIASES["design"]` is untouched, same reason.
- **`cli.py`**: the verb group and every identifier under it renamed (`cmd_plan_budget`,
  `cmd_plan_precheck`, `cmd_plan_render`, `cmd_plan_scaffold`, `plan_sub`, the `plan_action`
  dest). `terrastep design ...` no longer parses at all (Q6).
- **`budget.py`**: every docstring, message, and `doc.type` comparison updated; `default_slug`'s
  blank-title fallback changed from `"design"` to `"plan"` for the same reason.
- **`config.py`/`migrate.py`** (Q2): `MigrateConfig.plan_dir` → `legacy_dir`; the TOML key
  `[migrate] plan_dir` → `[migrate] legacy_dir`; the local `is_plan` → `is_substantive` in
  `migrate.py`. No repository configures this key today, so nothing else needed updating.
- **The corpus**: 0001 through 0007's frontmatter `type:` field rewritten to `plan`, mechanically
  (one line each). Their body prose is untouched, including 0007's own — this document explains a
  rename *between* the two words, so its prose keeps using both accurately; that is not leftover
  vocabulary, it is the subject of the document.
- **Generated docs and skill**: `skilldoc.py`'s generated prose (`SKILL_PROCEDURE`, the
  brain-budget procedure section, `references/*.md`) reworded throughout.
  `terrastep skill build` and `terrastep skill install --root . --force` both ran; `terrastep
  build` regenerated `STATUS.md`.
- **`readme.md`**: its two mentions updated.
- **Tests**: `tests/fixtures/0051_design_ok.md`'s `type:` field, and every `type: design`
  literal, CLI invocation (`cli.main(["design", ...])` → `["plan", ...]`), and assertion string
  across `test_core.py`, `test_budget.py`, `test_cli.py`, and `test_migrate.py` updated to match.
  One test (`fm-type`'s mutation) now mutates `type: plan` *to* `type: design`, to check that the
  retired value is itself rejected — a more direct check than the arbitrary value it used before.
- **Verified**: `core.TYPES == ("plan", "legacy", "note")`. `terrastep design budget` fails with
  `invalid choice: 'design'`, listing `plan` among the valid verbs. `grep -rn '"design"'
  src/terrastep/*.py` returns only the four `ROLE_ALIASES`/`EXPECTED_ROLES` lines named above.
  `terrastep.__version__` unchanged at `0.2.0`. Full suite: 217 passing (unchanged count — this
  design renamed tests, it did not add or remove any). `terrastep check` passes on this
  repository with brain budget on; this document itself precheck/render/checked clean, in
  budget, before being marked implemented.

No divergence from the plan as written.
