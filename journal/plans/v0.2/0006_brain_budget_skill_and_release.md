---
status: implemented
status_changed: 2026-09-29
type: plan
next: "None. Sequencing steps 1-4 are done (see \"What was built\" below). The pilot (step 5) was
  dropped by the owner as too much work for too little value."
---

# Brain budget D: agent procedure, generated documents and the 0.2.0 release

## Summary

This is the last of four brain budget designs (the proposal,
`journal/origin/brain_budget_proposal_v2.md`, section 17, doc D). It depends on 0005 for the
complete `terrastep design` verb set, the layer inside `terrastep check`, and the `In budget`
column.

This design teaches the agent the brain budget procedure through the generated skill, releases
terrastep 0.2.0, and turns brain budget on in terrastep's own `terrastep.toml`.

**The pilot (proposal section 15) is dropped.** The owner decided on 2026-09-29 that recording a
mental-effort rating after every design review, by hand, for an indefinite number of designs, is
too much ongoing work for what it would tell a one-owner repository right now. Section 15's
questions — is the flag hypothesis holding, is `max_retries = 2` the right spend — stay
unanswered until the owner decides they are worth that cost. Nothing here prevents starting the
pilot later; it would still read `policy_id` and `in_budget` straight from each design's
frontmatter.

## Scope

In scope:

- The procedure in proposal section 10.11, added to the generated `SKILL.md`.
- A generated `skill/references/brain_budget.md`.
- The new skill `description` (proposal 10.11, last paragraph).
- The regenerated `journal/terrastep_101.md`.
- The `CLAUDE.md` line "Plan and design work with the terrastep skill."
- The 0.2.0 version bump.
- Dogfooding: `enabled = true` in this repository.

Not in scope: the pilot (dropped, see Summary), a Codex skill (Q2), a tool that counts retries
(Q3), a new required `verification` section (Q4), and CI.

## The design

### The skill procedure

`skilldoc.py` adds the section "Writing design documents under a brain budget" to `SKILL.md`,
after "Writing a new `type: design` document". The text is proposal section 10.11. It holds no
limit values, because limits belong to each repository. The existing procedure also changes one
step: "Scaffold" now says to run `terrastep design scaffold` instead of writing the frontmatter
by hand. That works whether brain budget is on or off.

The skill `description` becomes: "Use when writing, reviewing, or checking a terrastep design
document, when asked to plan or design work in a repository with a terrastep.toml, or when a
task mentions terrastep, scan_dirs, brain budget, or the Blockers/Questions/Recommendations/
Sequencing shape."

### The generated reference

`skill/references/brain_budget.md` is generated from package constants, with no hand-written
tables:

- the four measures, their labels and their default limits, from `BudgetLimits` and
  `FORMAT_DEFINITION`;
- the working schema, with the current `schema_version` in its `const`, from
  `budget.working_schema()`;
- the `brain-budget-*` codes, from `core.FAILURE_CODES`;
- the edge rules and the pair test, as fixed text in `skilldoc.py`;
- the `[brain_budget]` configuration rows, from `CONFIG_HELP`.

`journal/terrastep_101.md` gains the same configuration rows and a short "Brain budget" part.
The existing staleness test covers both files.

### The 0.2.0 release

The permanent `In budget` column (0005) makes an existing user's `STATUS.md` stale.
`distribution.md` asks for a MAJOR bump for such a change. terrastep has not been distributed:
it has no git remote, no PyPI release, and no installation in another repository. So the bump is
0.2.0, and the MAJOR rule applies from the first real distribution onward.

0003, 0004 and 0005 each change `cli.py`, so each runs `terrastep skill build`. Their generated
files describe the new verbs but still stamp 0.1.0, until this design bumps the version. The owner
accepted this on 2026-09-29. No interim `0.2.0.devN` version is used.

One commit holds the bump in `__init__.py`, `terrastep skill build`, `terrastep skill install
--root . --force`, and `terrastep build` (`CLAUDE.md`, "Versioning and the generated
docs/skill"; `distribution.md` section 3).

### Dogfooding

After the release, this repository's `terrastep.toml` gets `[brain_budget] enabled = true`.
0001 and 0002 are `implemented`, and 0003 to 0006 will be `implemented` too. The layer skips
every one of them, so `terrastep check` still passes. The next terrastep design is the first one
written under the budget, with the procedure in the skill.

### The pilot: dropped

Skipped by owner decision (see Summary). No pilot note document is created. Q5's answer
("a `type: note` document, one row per design") is not built.

## Verification

- The skill staleness test passes. It covers `SKILL.md`, `references/brain_budget.md` and
  `terrastep_101.md`.
- `references/brain_budget.md` shows the current `schema_version`, and every `brain-budget-*`
  code in `FAILURE_CODES`.
- `SKILL.md` has no limit value.
- `terrastep_version` in `SKILL.md` is `0.2.0`.
- `terrastep check` passes on this repository with `enabled = true`.
- By hand, in a Claude Code session: a planning request in this repository loads the skill, and
  the agent runs `terrastep design budget` first. `pytest` cannot drive this, because it depends
  on the harness's skill loading (as in 0002).

## Blockers

None. Every step here uses verbs and rules that 0003 to 0005 deliver, and 0005 must be
implemented before this design starts. The release decision is already made (Q6).

## Questions

### Q1 — What does `max_retries` bound?

**Recommendation:** one setting for token spend, per design, shared by the precheck and the
check (I6). It covers format fixes and re-split attempts. It is not spent on an irreducible
coupled cluster.

### Q2 — When does terrastep ship a Codex skill?

The CLI and the rules do not depend on the agent (I21, OQ6).

**Recommendation:** later, as its own design, when a real repository uses Codex. `terrastep
skill install` does not write `.agents/skills/terrastep/` in 0.2.0.

### Q3 — Does terrastep record the retries an agent used?

With a soft budget, the retry count is evidence that the agent tried (OQ8).

**Recommendation:** report it in the chat summary only, so `terrastep check` stays read-only
and terrastep keeps no state between runs. The pilot copies it from the chat report.

### Q4 — Must a budgeted design have a `verification` section?

terrastep does not require one today (OQ9).

**Recommendation:** no. The scaffold writes one, and the layer stays additive.

### Q5 — Where do the pilot records live?

**Recommendation:** a `type: note` document in `journal/plans/`, one row per budgeted design.
The limits change only through a later design. **Moot:** the owner dropped the pilot itself on
2026-09-29 (see Summary), so this was never built.

### Q6 — What is the version number?

**Recommendation:** 0.2.0. The owner decided this on 2026-09-29 (OQ10). The MAJOR rule in
`distribution.md` applies from the first real distribution onward.

## Recommendations

1. `max_retries` bounds token spend per design and is not spent on an irreducible cluster (Q1).
2. Defer the Codex skill to its own design (Q2).
3. Report retries in the chat summary only (Q3).
4. Do not require a `verification` section (Q4).
5. Keep pilot records in a `type: note` document, if the pilot is ever started (Q5, moot for now).
6. Release 0.2.0 (Q6).

## Sequencing

1. The skill procedure, the new `description`, and the changed "Scaffold" step in `skilldoc.py`.
2. The generated `references/brain_budget.md` and the new part of `terrastep_101.md`.
3. The version bump to 0.2.0, `terrastep skill build`, `terrastep skill install --root .
   --force`, `terrastep build`, the full suite and `terrastep check`. One commit.
4. `enabled = true` in this repository's `terrastep.toml`, and the `CLAUDE.md` line. Check the
   skill by hand in a Claude Code session.

The pilot (proposal section 15) is dropped; there is no step 5.

## What was built (2026-09-29)

Steps 1-4 done, each as recommended, no scope changes. Step 5 (the pilot) was dropped by the
owner before this design was implemented — see Summary and Q5.

- **`skilldoc.py`**: `SKILL.md` gained the "Writing design documents under a brain budget"
  section (proposal 10.11, verbatim, no limit values), inserted right after "Writing a new
  `type: design` document". That section's own "Scaffold" step now says to run
  `terrastep design scaffold` instead of hand-writing frontmatter — true whether brain budget is
  on or off. The skill's `description` was replaced with the proposal's exact new text.
- **`skill/references/brain_budget.md`** (new, generated): the four measures and their default
  limits, the live ledger schema (with the running `schema_version` in its `const`), the edge and
  prerequisite rules as fixed prose, every `brain-budget-*` failure code from `FAILURE_CODES`, and
  the `[brain_budget]` configuration rows — the last of these now shared with `_config_table` via
  one helper (`_brain_budget_config_rows`), so the two tables cannot drift apart.
- **`journal/terrastep_101.md`**: a new "3. Brain budget" part (bumping "How to use them" to "4."),
  with the same measures table.
- **`CLAUDE.md`**: a "Planning and design work" section with the line the design specifies.
- **Version**: `__init__.py` bumped to `0.2.0`. `terrastep skill build`, `terrastep skill install
  --root . --force`, and `terrastep build` all ran in the same change as the bump, per `CLAUDE.md`'s
  own rule that a version bump is a content change to every generated file.
- **Dogfooding**: `[brain_budget] enabled = true` added to this repository's own `terrastep.toml`.
  0001-0006 are all `implemented` (0006 marked so in this same commit), so the layer's
  `planning`/`ready` status scope skips every one of them; `terrastep check` still passes.
- **Verified by hand, in this Claude Code session**: after this repo's own `.claude/skills/terrastep/`
  was refreshed via `terrastep skill install --force`, the skill listing shown to the session
  updated to the new `description` text before this paragraph was written — confirming the
  harness picks up the regenerated file, not a cached copy.
- **One test update**: `test_render_all_produces_the_four_expected_files` renamed and updated to
  expect the fifth generated file.

No divergence from the plan as written, apart from dropping the pilot (an explicit owner decision,
not a technical finding). `enabled = true` is now this repository's setting, so the next terrastep
design is the first one written under the budget.
