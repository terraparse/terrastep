---
status: planning
status_changed: 2026-09-29
type: design
next: Owner reviews Q1-Q6.
---

# Brain budget D: agent procedure, generated documents and the 0.2.0 release

## Summary

This is the last of four brain budget designs (the proposal,
`journal/origin/brain_budget_proposal_v2.md`, section 17, doc D). It depends on 0005 for the
complete `terrastep design` verb set, the layer inside `terrastep check`, and the `In budget`
column.

This design teaches the agent the brain budget procedure through the generated skill, releases
terrastep 0.2.0, turns brain budget on in terrastep's own `terrastep.toml`, and starts the pilot
that tests the limits and the flag hypothesis.

## Scope

In scope:

- The procedure in proposal section 10.11, added to the generated `SKILL.md`.
- A generated `skill/references/brain_budget.md`.
- The new skill `description` (proposal 10.11, last paragraph).
- The regenerated `journal/terrastep_101.md`.
- The `CLAUDE.md` line "Plan and design work with the terrastep skill."
- The 0.2.0 version bump.
- Dogfooding: `enabled = true` in this repository.
- The pilot plan (proposal section 15).

Not in scope: a Codex skill (Q2), a tool that counts retries (Q3), a new required
`verification` section (Q4), and CI.

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

One commit holds the bump in `__init__.py`, `terrastep skill build`, `terrastep skill install
--root . --force`, and `terrastep build` (`CLAUDE.md`, "Versioning and the generated
docs/skill"; `distribution.md` section 3).

### Dogfooding

After the release, this repository's `terrastep.toml` gets `[brain_budget] enabled = true`.
0001 and 0002 are `implemented`, and 0003 to 0006 will be `implemented` too. The layer skips
every one of them, so `terrastep check` still passes. The next terrastep design is the first one
written under the budget, with the procedure in the skill.

### The pilot

The pilot follows proposal section 15. For each design written under the budget, the owner
records: the policy (`policy_id`), `in_budget`, the measures, the retries used (from the chat
report, Q3), the active review time, and one nine-point mental-effort rating right after the
review. For each flagged design, the owner also records whether the excess was an irreducible
coupled cluster. The records go into a `type: note` document in `journal/plans/`, one row per
design.

The pilot has no fixed end. This design reaches `implemented` when the procedure ships and the
first budgeted design is written. The pilot's results go into a later design that proposes limit
changes, one limit at a time.

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
The limits change only through a later design.

### Q6 — What is the version number?

**Recommendation:** 0.2.0. The owner decided this on 2026-09-29 (OQ10). The MAJOR rule in
`distribution.md` applies from the first real distribution onward.

## Recommendations

1. `max_retries` bounds token spend per design and is not spent on an irreducible cluster (Q1).
2. Defer the Codex skill to its own design (Q2).
3. Report retries in the chat summary only (Q3).
4. Do not require a `verification` section (Q4).
5. Keep pilot records in a `type: note` document (Q5).
6. Release 0.2.0 (Q6).

## Sequencing

1. The skill procedure, the new `description`, and the changed "Scaffold" step in `skilldoc.py`.
2. The generated `references/brain_budget.md` and the new part of `terrastep_101.md`.
3. The version bump to 0.2.0, `terrastep skill build`, `terrastep skill install --root .
   --force`, `terrastep build`, the full suite and `terrastep check`. One commit.
4. `enabled = true` in this repository's `terrastep.toml`, the `CLAUDE.md` line, and the pilot
   note. Check the skill by hand in a Claude Code session.
5. Write the next terrastep design under the budget. Record it in the pilot note.
