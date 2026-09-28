---
status: closed
status_changed: 2026-09-25
type: note
closed_reason: reference
---

# Perry conventions: the method sections (excerpt)

Rules Claude must apply on any future task of the relevant kind — not just the task that produced them. Always loaded (imported from root `CLAUDE.md`), by deliberate choice: these are referenced by name constantly enough that the risk of a missed check outweighs the token cost of loading them every session. See `journal/misc/claudemd_redesign.md` for the reasoning behind this file's existence.

> Excerpt copied 2026-09-25 from Perry's `docs/conventions.md`. Only the sections that describe the
> working method are kept. Perry-specific sections (pipeline stage names, "policy", run stories,
> the architecture map) are left out. Perry's copy stays the source until terrastep takes over.

## How to review a refactoring planning document (standing preference)

**Stated by the project owner 2026-08-18. This applies to every planning
document under `journal/v0-6/refactoring/` and any successor directory.**

When you review a planning doc, the review is not finished until the document
carries two things:

1. **A blockers section** — what must be settled before implementation, meaning
   anything where a wrong answer produces a system that is quietly *incorrect*
   rather than merely suboptimal.
2. **An open-questions section** — what is genuinely undecided but where any
   answer yields a working system.

**Every blocker and every question gets an explicit recommendation.** Not a
survey of options, not "it depends" — a recommendation, with the reasoning that
supports it. The point is that a decision becomes a *review* of a proposal rather
than a fresh analysis from a cold start.

**Ground each recommendation in this project's own principles and history**, not
in general software-engineering advice. This file and the journal are full of
specific, expensive lessons, and they are the standard to argue from. The ones
that recur most:

- A value written with no reader, or a state that cannot be reached, is the
  defect this codebase has shipped a dozen times. Grep for a reader before
  believing a field does something.
- A test that agrees with the bug proves nothing; a negative control that does
  not fail has proved nothing.
- Measure before tuning, and set the bar before seeing the data.
- Do the reporting half first — surface what a real run observes, then write the
  fix from evidence.
- Prefer refusing or raising over guessing a survivor.
- Ordering dominates capping when the scarce resource is reviewer attention.
- Removing dead code invalidates prose that cites it; a symbol's dependents
  include comments, docs, and journal entries.

**If a review turns up no blockers, say so explicitly and say why** — an absent
section reads as an unfinished review, not a clean bill of health. The same
applies to open questions.

**Keep the document at planning stage** unless told otherwise, and follow GR-2:
annotate with dated notes rather than rewriting history in place. The exception
is a section that has become unreadable through accumulated review passes — then
rewrite it clean, say that you did, and state what it supersedes.


## BQRS — the required shape for a code-development plan (standing preference)

**Stated by the project owner 2026-09-10, naming an acronym for the shape the
section above already required in substance.** When the owner asks for "our
typical refactoring implementation plan" or invokes **BQRS** by name, the
document's decision part is exactly these four sections, in this order, placed
after whatever explanatory sections the idea needs (the problem, the design, the
scope — see `journal/misc/status_and_terraparse_rfcs.md` for the allowed
formats) and before any dated notes:

1. **Blockers** — as defined above: anything where a wrong answer produces a
   system that is quietly *incorrect*, not merely suboptimal. Each one carries
   its own recommendation and reasoning, grounded in this project's own history
   per the section above, not general advice.
2. **Questions** — genuinely open, any answer yields a working system. Same
   rule: each carries an explicit recommendation.
3. **Recommendations** — a consolidated, skimmable list restating each
   blocker's and question's recommendation in one place, in priority order and
   naming each item's ID (`B2`, `Q1`) — a blocker already cleared needs no entry —
   **without re-arguing them**. This section exists for a reader who wants the
   decision, not the reasoning already given inline under B/Q.
4. **Sequencing recommendation** — when this should land relative to other
   in-flight or planned work: what must happen first, what it must not be
   bundled with, what can proceed in parallel. This generalizes a pattern
   already used ad hoc across many journal entries (e.g. "must land AFTER the
   next lexical run") into an explicit, always-present closing section rather
   than something only some plans happen to include.

**BQRS is the authoring template; the section above is the review discipline
it exists to satisfy** — the two are not in tension, and a document that
satisfies BQRS automatically satisfies the blockers/questions requirement
above. First used in
[`resume_stage_shortcuts.md`](journal/v0-6/refactoring/resume_stage_shortcuts.md).


## TerraParse RFCs and STATUS.md (standing preference)

**Stated by the project owner 2026-09-23.** Every document under `journal/`
carries a frontmatter block. `journal/STATUS.md` is the generated index of
them, and `scripts/check_status.sh` enforces the format. The design, the
influences and the reasons are in `journal/misc/status_and_terraparse_rfcs.md`.
This section holds only what a task must do.

- **When picking work back up, read `journal/STATUS.md` first.** It lists every
  document, newest status change first, with `ready` and `in-progress` on top.
- **A new plan doc gets a number and a type.** Name it `NNNN_slug.md`, using the
  number from `venv/bin/python scripts/build_status.py --next-id` (1 to 48 are
  reserved for renumbering legacy docs). Set `type:` to `design`. A small idea is a
  short design doc. A choice among options goes in the Questions section of a
  design doc, with the options and a recommendation. The decision part follows
  BQRS above. Other types are `note` and `legacy`.
- **A status change is a frontmatter edit.** Set `status` and `status_changed`
  when a doc's state changes: `planning`, `ready`, `in-progress`,
  `implemented`, `closed` (`closed` needs `closed_reason`). A design doc starts in
  `planning`. A note is only `in-progress` or `closed`. Never edit
  `STATUS.md`. Regenerate it with `venv/bin/python scripts/build_status.py`.
- **Claude never sets `ready`.** `planning` to `ready` is the owner's approval.
  The check cannot tell who edited a file, so this is a rule and not a gate. The
  check does refuse `ready` or `in-progress` while a blocker is tagged `[open]`.
- **Tag every blocker `[open]` or `[resolved]` on its first line.** Give every
  question and every open blocker an explicit recommendation.
- **Before calling a task done, run `scripts/check_status.sh`.** It must print
  OK. This applies to any task that adds, edits or closes a journal doc. Two
  hooks enforce it. A Claude Code `Stop` hook (`.claude/settings.json`) refuses
  to end a turn while the check fails and `journal/` has uncommitted changes. A
  git pre-commit hook refuses a commit whose staged `journal/` fails. Install the
  git hook once per clone with `scripts/install_git_hooks.sh`. Use
  `git commit --no-verify` only if the owner asks.
- **Do not retrofit old docs.** A `type: legacy` doc keeps its old shape. Upgrade
  one only when work reopens it, and record the upgrade as a dated note.
- **A passing check is not a passing review.** The check proves the structure is
  present. It does not prove the reasoning rests on this project's own history.
  The review discipline above still applies.


## How to cite a section (standing preference)

**Stated by the project owner 2026-09-01**, because a bare section symbol with no
document attached is ambiguous in a repository holding forty numbered notes, and
was repeatedly confusing in practice.

**The rule: a section reference always names its document.** Never a bare `§8` or
`S8`, in prose, in code comments, or in chat.

```
S8 in lexical_ranking_upgrades.md          <- section 8 of that note
S4a in lexical_ranking_upgrades.md         <- lettered subsection, same form
B4 in discovery_blacklist_refit.md         <- blockers keep their own IDs
Q5 in lexical_ranking_upgrades.md          <- so do open questions
F1 in research_agenda.md                   <- so do agenda items
```

**This resolves a collision specific to this codebase, and that is why the
document name is not optional.** `S01`-`S15` already mean *pipeline stages* —
`S07` acquisition, `S13` comparability — and those are persisted values in
`research_run_stages.stage_name`. So `S13` and `S13 in batch_extraction.md` are
different things, and **the trailing `in <file>` is the entire disambiguator**.
Drop it and the reader cannot tell a stage from a section.

- **A pipeline stage is written bare**: `S07`, `S13`, or `S07_ACQUIRE`. Never
  with `in <file>`.
- **A document section always carries `in <file>`.** If naming the document feels
  redundant because you just named it, name it anyway — the redundancy costs a
  few words and the ambiguity costs a reader.
- **Cross-directory references take enough path to be found**:
  `S11 in v0-5/archival_fetch_fix.md`. A bare filename is fine within
  `journal/v0-6/refactoring/`.

**Two carve-outs, both because the document is already named:**

- **`spec §4.2`** stays as-is for the v0.4/v0.5 specs. The word "spec" names the
  document, the form appears in hundreds of existing citations, and those specs
  number themselves with `§`. Where ambiguity is possible, write
  `§4.2 of perry_v0-4_spec.md`.
- **CLAUDE.md's own sections are titled, not numbered.** Cite them by title:
  *CLAUDE.md's "Projects" section*.

**In conversation, the same rule holds, plus one addition: never use a section
symbol for something said in the chat rather than written in a file.** Say "as I
noted earlier" or quote it. A reader who goes looking for a section that exists
only in the transcript has been sent nowhere.


## Maintaining `CLAUDE.md` (standing preference)

**Added 2026-09-14, when the root file was split from 5,592 lines down to a
thin, always-loaded core — see `journal/misc/claudemd_redesign.md` for the full
reasoning.** This entry exists so the same accretion cannot restart.

**The failure this rule prevents has an exact, greppable signature.** Every
one of the ~45 oversized sections the 2026-09-14 split removed was a `##`
heading ending in a literal `(YYYY-MM-DD)` date. That is what a change
write-up looks like when it lands in the wrong file, and it is what
`scripts/check_claude_md.sh` (below) actually checks for.

**The rule:**

- **Root `CLAUDE.md` and this file never receive a dated, per-change
  narrative section again.** Not "shrink it later" — never. If you are
  about to add a `##` heading with a date in it to either file, stop.
- **A change gets exactly two things by default**: an entry in its
  `journal/v0-6/refactoring/*.md` (or successor directory's) design doc —
  already required by this project's BQRS discipline above — and one line
  in `journal/CHANGELOG.md` pointing at that doc. Nothing else.
- **A change earns a line in this file or in a module-scoped
  `perry/*/CLAUDE.md`** only if it states a reusable rule or invariant a
  *future, unrelated* task must apply — not a record that the change
  happened. Use the same test BQRS already uses for a blocker: would
  getting this wrong on a future task be quietly *incorrect*, not merely
  a missed opportunity to know history? If yes, it's a rule and belongs
  here or in a module file. If it's just interesting or hard-won history,
  it belongs in the design doc and the changelog line, not here.
- **Target size for the root file: under ~300 lines.** If `CLAUDE.md`
  exceeds that, something has drifted back into it — audit before adding
  more, don't just keep appending.

**Enforcement, not just a written rule.** `scripts/check_claude_md.sh`
greps `CLAUDE.md` and `docs/conventions.md` for a `##`-level heading
containing a `YYYY-MM-DD` pattern and fails loudly if it finds one. Run it
before committing either file, or wire it as a `PreToolUse` hook on
`Edit`/`Write` against those two paths (see this environment's own
`settings.json` hook mechanics — and validate the hook config with
`jq -e . ~/.claude/settings.json` immediately after editing it, since a
stray comment or trailing comma silently voids the whole hooks file with
no error). A written rule is what explains *why*; the self-referential
note at the top of `CLAUDE.md` catches the moment of temptation; this
check is what actually stops it under time pressure or a compacted
context window — which is the condition under which the file grew the
first time.
