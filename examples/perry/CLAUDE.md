# CLAUDE.md — Perry development & operations orientation

This file is for whoever (human or Claude) picks this project back up next.
**It is deliberately thin.** It used to be a 5,592-line changelog; that was
split apart on 2026-09-14 because most of it was history relevant to one
task, force-loaded on every task — see `journal/misc/claudemd_redesign.md` for the full
reasoning. This file now holds only what's true regardless of task and what
Claude must apply on every relevant task. Everything else lives one link
away, read when the task actually touches it.

**Before adding a dated `## ... (YYYY-MM-DD)` section here: don't.** Write
the design-doc entry and the one-line `journal/CHANGELOG.md` index entry
instead. See "Maintaining CLAUDE.md" in `docs/conventions.md`. Run
`scripts/check_claude_md.sh` if unsure.

## What this is

Perry is the Python implementation of
[`journal/misc/perry_v0-4_spec.md`](journal/misc/perry_v0-4_spec.md) (the
v0.4 baseline spec) as amended by
[`journal/v0-5/spec_v0-5.md`](journal/v0-5/spec_v0-5.md) (the v0.5 SDD,
authoritative wherever the two disagree) and by the design docs under
[`journal/v0-6/refactoring/`](journal/v0-6/refactoring/) for everything
since. It's a deterministic staged pipeline that sources human-reviewable
evidence for financial model variables. Read the v0.4 spec, then the
v0.5 SDD, if you haven't — the rest of this file assumes both.

## How this file is organized

- **`docs/conventions.md`** (always loaded, imported below) — standing
  rules: how to review a planning doc, the BQRS shape for a plan, how to
  cite a section, how to name a pipeline stage, the "policy" ambiguity, the
  run-story genre, and how to maintain this file. Read this before writing
  a planning doc, citing a section, or naming a stage.
- **`docs/architecture_map.md`** (imported below) — spec section → code.
  Read on nearly every task.
- **`docs/environment.md`** — setup, dependency pinning, provider API
  quirks, the before-first-live-run checklist, regenerating the schema.
  Read when touching environment/dependencies/providers, **or before
  running any one-off script/command that calls boto3 or hits the database
  directly outside `perry`/`pytest`** — `.env`'s values don't all reach the
  process the same way, and guessing which do costs a debugging round.
- **`docs/known_gaps.md`** — the living "not yet done / known gaps" list.
  Read before building near an area that might already have a known,
  unresolved gap.
- **`journal/CHANGELOG.md`** — one line per change, newest first, each
  linking to the design doc that carries the full account. Grep this for
  the topic you're touching, then open the linked doc(s) under
  `journal/v0-6/refactoring/` or `journal/v0-5/`.
- **`journal/STATUS.md`** — generated index: every journal doc's `status`,
  newest change first, `ready` and `in-progress` on top. **Read it first when
  picking work back up.** How to write a doc's frontmatter is in
  `docs/conventions.md`'s "TerraParse RFCs and STATUS.md" section.
- **Module-scoped `CLAUDE.md` files** (`perry/specs/CLAUDE.md`,
  `perry/db/CLAUDE.md`, `perry/coordinator/CLAUDE.md`,
  `perry/classify/CLAUDE.md`) — load automatically when you read files in
  those directories. Dense, module-specific invariants that are easy to get
  wrong; not history.

@docs/conventions.md
@docs/architecture_map.md
