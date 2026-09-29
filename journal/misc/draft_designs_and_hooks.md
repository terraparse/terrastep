# Unfinished designs and the hooks: background and options

A note for later review, written 2026-09-29. Low priority, and no action is planned. It is outside
`scan_dirs`, so it has no frontmatter.

It expands item 6 of the observations made after 0003 to 0006 were written: an unfinished design
trips the Stop hook and the pre-commit hook. With brain budget, this happens more often.

## Background

### What the two hooks do

- **Stop hook** (`integrations/claude/stop_hook.sh`). At the end of each Claude Code turn, it runs
  `terrastep check --if-changed`. If `scan_dirs` has uncommitted changes and the check fails, it
  returns `{"decision": "block", "reason": ...}`. Claude Code then does not end the turn, and the
  agent gets the last 30 lines of the check output. On the next stop request `stop_hook_active` is
  true, so the hook lets the turn end. The hook blocks each turn at most once.
- **Pre-commit hook** (`hooks.precommit`). It checks the staged snapshot of `scan_dirs`. Any failure
  blocks the commit. `git commit --no-verify` skips the hook.

Neither hook is installed in this repository today. There is no `.git/hooks/pre-commit`, and
`.claude/` has no settings file with a Stop hook. The issue applies to a repository that runs
`terrastep install-hooks` and registers the Stop hook shim.

### Why an unfinished design fails the check

Today, `terrastep check` fails on a design with empty Blockers or Questions sections. I checked a
file shaped like the proposal's scaffold (proposal section 5.7) with terrastep 0.1.0 on
2026-09-29. It fails three times:

- `body-empty` for Blockers;
- `body-empty` for Questions;
- `stale-index`, because the new file is not in `STATUS.md` yet.

With brain budget (0005), the same file also fails `brain-budget-draft-marker`. It keeps failing
until every `<!-- terrastep:draft -->` is replaced.

### Why brain budget makes it more frequent

The brain budget procedure creates the file early, before any prose (proposal section 10.5). The
agent scaffolds, declares, prechecks, writes the prose, renders, and checks, in that order. During
most of those steps, the file exists in `scan_dirs` and fails the final check. That is by design,
because the precheck is the stage meant for unfinished files.

The turn can end while a file is in that state:

1. **The agent stops to ask the owner something**, for example which of two splits to use. The
   question ends the turn, and the Stop hook fires.
2. **A multi-design request is only partly done.** The agent finishes 0007, scaffolds 0008, and
   then the turn ends: the owner interrupts, or the agent runs out of turn budget.
3. **The retries run out.** The agent delivers a failed draft (proposal section 10.6). The proposal
   expects the Stop hook to block once here and then let the turn end.
4. **The owner wants to commit work in progress**, for example to switch machines. The pre-commit
   hook blocks it.

### What the block costs

- **One extra model round per turn.** The agent reads the block reason and must answer it.
- **Unwanted edits.** The block reason says "Fix the failures below, then stop." An agent that
  stopped to ask the owner a question can then write prose to clear `body-empty` or the draft
  markers. That goes against the procedure ("Do not write prose while the precheck fails") and
  fills in answers the owner has not given yet.
- **A blocked commit for work in progress.** The workarounds are `--no-verify`, or keeping the
  unfinished file unstaged.

Case 3 is intended. Cases 1, 2 and 4 are the cost.

## Options

The options are listed from cheapest to most invasive. They can be combined.

### A. Skill procedure: settle questions before scaffolding

Add rules to the brain budget procedure in `SKILL.md` (0006):

- Ask the owner every question that could change the decomposition before running
  `terrastep design scaffold`.
- Take one design at a time from scaffold to a passing `terrastep check` before scaffolding the
  next one.

- **Changes:** text in `skilldoc.py` only.
- **Behaviour change:** fewer turns end with a file half done. Interruptions (case 2) and failed
  drafts (case 3) still trip the hook.
- **Risk:** none in code. The agent may not follow it every time.

### B. Stop hook: a separate message for drafts

In `stop_hook.sh`, when every failure is on a file that still has a draft marker, use a different
block reason: "These designs are unfinished drafts. If you are waiting for the owner, say so and
stop. Do not write prose to clear these failures." The hook still blocks once.

- **Changes:** the shim, plus a way to tell draft failures apart. That could be
  `terrastep check --format json` (0005) read with `jq`: take the files with a
  `brain-budget-draft-marker` failure.
- **Behaviour change:** removes the unwanted edits. It keeps the extra model round.
- **Risk:** low. It depends on the JSON report from 0005.

### C. Stop hook: skip files that are marked as drafts

Add `terrastep check --skip-drafts`. A file that still has a draft marker is reported as a warning
("unfinished draft"), not as failures. The Stop hook shim passes the flag. The pre-commit hook does
not.

- **Changes:** one flag in `cli.py`, a filter in `core.check_corpus` (0005), and the shim.
- **Behaviour change:** cases 1 and 2 no longer block the turn. Case 3 still blocks once when the
  failed draft has no markers left. The pre-commit hook still blocks unfinished files.
- **Risk:** an abandoned draft is never flagged at turn end. It is still flagged at commit time,
  and `terrastep check` without the flag still fails. `stale-index` needs a rule too: either skip
  it when the only new files are drafts, or keep it (`terrastep build` is cheap).

### D. Pre-commit: allow drafts to be committed

The same `--skip-drafts` in the pre-commit hook, so unfinished designs can be committed.

- **Behaviour change:** fixes case 4.
- **Risk:** higher. Draft files reach history and `STATUS.md`. Other readers see
  `status: planning` documents that are only skeletons. It also weakens the "a committed document
  passes `terrastep check`" rule that the pre-commit hook exists for. I would not do this without a
  distinct status (option E).

### E. A distinct status for unfinished designs

Add a status such as `drafting` before `planning`. Scaffold writes `status: drafting`. The final
check applies relaxed rules to `drafting` (no `body-empty`, no draft-marker failure), and `render`
or the agent moves the design to `planning` when it passes.

- **Changes:** `core.STATES`, the rules, the index tables, the skill, and `migrate`. It is a change
  to terrastep's format, so it needs its own design.
- **Behaviour change:** the state is explicit in the frontmatter and in `STATUS.md`. Options C and
  D become rules about `drafting` instead of rules about draft markers.
- **Risk:** the largest change. A new status is a new way to leave a document unfinished for a
  long time. The in-progress cap has no counterpart for it.

### F. Scaffold outside `scan_dirs`, then promote

Scaffold into a staging directory outside `scan_dirs`, and add `terrastep design promote` to move
the file in once it passes.

- **Behaviour change:** unfinished files are invisible to both hooks.
- **Risk:** high. `next_id` cannot see staged files, so two staged designs can take the same number.
  The precheck needs the corpus to resolve `depends_on`, and the prerequisite gate reads scanned
  documents only. I do not recommend this option.

## Suggested order, if this becomes a problem

1. **A** when 0006 writes the skill procedure. It costs nothing, and it can be done without waiting
   for evidence.
2. **B** if the pilot (0006) shows agents writing prose to clear the Stop hook.
3. **C** if the extra model round shows up as a real cost in the pilot's token records.
4. **E** only if work in progress needs to be committed often. **D** only together with E.

## Evidence to collect during the pilot

- How many turns end with a Stop hook block on an unfinished design, and which of cases 1 to 3
  caused each one.
- Whether the agent edited prose or declarations in the round after the block.
- How often the owner used `--no-verify` for design work in progress.
