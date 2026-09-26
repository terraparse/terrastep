# Handoff: from Perry to terrastep

**Written 2026-09-25 by Claude, at the end of the session that built the format in the Perry repository.** Read this first. It says
what terrastep inherits, how the pieces work today, what is specific to Perry, and what is still unproven.

**Audience:** the first Claude Code or Codex session that works in this repository, and the owner.

## 1. What terrastep is for

`readme.md` names it: TerraParse Standardized Enhancement Proposals ("terrastep"). It is a method and a format for working with LLMs
and agents on software. In Perry it was called "TerraParse RFCs", and the design note in `docs/origin/` uses that
name. It is the same thing. `terrastep` will be its name moving forward.

The owner's goal for this repository has three parts:

1. **Standards.** The document format, the status lifecycle, and the rules for writing and reviewing a plan. We want the standards to be independent of implmentation to make it easier to implement with different technologies.
2. **A Python CLI library** that enforces and serves those standards in any repository: check, build the index, give
   the next number, migrate old docs. At this starting point, this will be the technology we use to implement.
3. **Claude and Codex skills** that call that CLI, so an agent writes and reviews docs in the format without reading
   the whole standard each session. These are pragmatic toolks developed to bring the implementation of standards via the python CLI library come to life. We are not wedded to them forever as the outcome. The important parts are the standards; we build tools based on ever-changing developer patterns.

Today only the first part exists, as prose in Perry, with a working prototype of the second part as loose scripts.
Nothing here is packaged yet.

## 2. Where it came from

Everything was built in Perry (`~/dev/projects/py/perry`) on 2026-09-23 and 2026-09-24:

- Perry commit `dde1a78` ("Switch to TeraParse RFC software development method") holds the format, the scripts, the
  migration of 126 existing journal docs, and the generated `journal/STATUS.md`.
- The two enforcement hooks (a Claude Code `Stop` hook and a git pre-commit hook) were built after that commit. They
  are in Perry's working tree, not yet committed when this copy was made. The copies here include them.

**Perry stays the first user.** It keeps its own copy of the scripts until terrastep can replace them. Do not break
Perry's workflow while building here. Perry's docs are the corpus to test against.

## 3. What is in this repository

| Path | What it is |
|---|---|
| `docs/origin/status_and_terraparse_rfcs.md` | **The design note. Read it second.** The problem, the format, the influences (PEP, KEP, Rust RFC, ADR, Kanban, Shape Up), why it fits one developer and many LLMs, every decision with its reason, and the full implementation record. |
| `docs/origin/teaching_repos_my_claude_method.md` | The earlier note on rolling the method out to many repos: a plugin for behavior, a copier template for files, a `MIGRATIONS.md`. Its Part 2 is the plan terrastep now carries. Not started. |
| `seed/scripts/` | The prototype, copied unchanged from Perry. See section 4. |
| `seed/tests/` | 91 tests and one passing fixture. They run here as-is (checked 2026-09-25 in terrastep's own `venv/`: 91 passed). The count was 87 with three fixtures before `pitch` and `decision` were removed. |
| `examples/perry/CLAUDE.md` | Perry's root `CLAUDE.md`: an example of a thin always-loaded file that points to everything else. |
| `examples/perry/conventions_method_excerpt.md` | The method sections of Perry's `docs/conventions.md`: review discipline, BQRS, the TerraParse section, section citation, maintaining `CLAUDE.md`. |
| `examples/perry/claude_settings.json` | Perry's `.claude/settings.json`: the two hooks as registered. |
| `examples/perry/journal/STATUS.md` | A real generated index, 128 docs. |
| `examples/perry/journal/resume_stage_shortcuts.md`, `s3_prefix_split.md` | The two docs used as the "two-doc test": the closest real examples of the BQRS shape. Both carry `type: legacy` frontmatter from the migration. |
| `examples/perry/journal/status_migration_proposal.md` | The reviewed migration table for Perry's 126 docs. Shows what `propose_frontmatter.py` produces. |

## 4. How it works today

### The format, in one screen

Every doc under the scanned directory starts with frontmatter:

```yaml
---
status: planning            # planning | ready | in-progress | implemented | closed
status_changed: 2026-09-23
type: design                # design | legacy | note
next: One line. The next action, or what blocks it.
blocked_by: other_doc.md    # optional
superseded_by: new_doc.md   # optional
closed_reason: superseded   # when closed: superseded | rejected | withdrawn | reference
---
```

- **The plan type** (`design`) gets a body check. Until 2026-09-25 `pitch` and `decision` existed too. A small idea is now a short `design` doc, and a choice among options goes in a Questions item. `legacy` (a plan older than the format) and `note`
  (anything that is not a proposal) do not.
- **States.** A `design` doc starts in `planning` (the `idea` state was removed 2026-09-25). A `note` is only `in-progress` or `closed`.
- **A plan body** has explanatory "front" sections, then exactly four decision sections in order (Blockers,
  Questions, Recommendations, Sequencing = BQRS), then optional dated notes.
- **Front sections have roles, not fixed titles.** An alias table maps headings to eight roles: summary, motivation,
  scope, design, alternatives, evidence, verification, history. The `design` type requires a summary or a motivation, and warns when design or scope is missing.
- **Every blocker carries `[open]` or `[resolved]`.** `ready` and `in-progress` are refused while any blocker is
  `[open]`.
- **Plan files are numbered** by filename prefix, `NNNN_slug.md`. New numbers start at 49 in Perry. 1 to 48 are
  reserved there for renumbering legacy docs.
- **`STATUS.md` is generated, never edited.** Blocks: Active (`ready`, `in-progress`), Planning (the owner's review
  queue, with a count), All (newest first), and docs without frontmatter.
- **Only the owner moves a doc from `planning` to `ready`.** This is a written rule, not a gate. No script can tell
  who edited a file.

The full rule list, with failure codes, is in the design note, under "The check script".

### The scripts (`seed/scripts/`)

| Script | Role | Becomes, in the CLI |
|---|---|---|
| `rfc_lib.py` | The one parser and every rule. Reads files, never writes. `render_status` builds the index text. | The library core. |
| `check_status.py` / `check_status.sh` | Runs all rules plus a `stale-index` check. `--survey [DIR]` prints how every heading classifies. `--root` points at another tree. | `check`, `survey` |
| `build_status.py` | Writes `STATUS.md`. `--next-id` prints the next free number. | `build`, `next-id` |
| `propose_frontmatter.py` | One-time migration: writes a proposal table from each doc's free-text `Status:` line, git dates, and `CHANGELOG.md` links. `--apply` reads the reviewed table back and prepends frontmatter. Refuses a doc that already has frontmatter. | `migrate propose`, `migrate apply` |
| `check_status_stop_hook.sh` | Claude Code `Stop` hook. Blocks the end of a turn when the journal has uncommitted changes and the check fails. Lets go when `stop_hook_active` is true. Needs `jq`. | Shipped by the Claude plugin. |
| `git-hooks/pre-commit`, `install_git_hooks.sh` | Checks the **staged** snapshot (exported with `git checkout-index`), not the working tree. Runs only when the commit touches guarded paths. | `install-hooks`, or a pre-commit framework entry. |
| `check_claude_md.sh`, `check_claude_md_hook.sh` | Perry's older guard: no dated `## ... (YYYY-MM-DD)` heading in `CLAUDE.md` or the conventions file. The same "a check beats a rule" idea; a candidate for the standard too. | Optional rule. |

**Dependencies:** Python 3.11+, PyYAML, pytest (tests), git, bash, `jq` (the `Stop` hook and the CLAUDE.md hook).

### The workflow in Perry

1. When work resumes, read `journal/STATUS.md` first.
2. A new plan: take `--next-id`, name the file `NNNN_slug.md`, pick a type, write the front sections and BQRS.
3. A status change is a frontmatter edit. Then regenerate `STATUS.md`.
4. The `Stop` hook and the pre-commit hook run the check. It must print OK before a task is done.
5. A passing check is not a passing review. The review discipline (every item has a recommendation grounded in the
   project's own history) is still a human or skill job.

## 5. What is specific to Perry and must become configuration

These are the places the prototype assumes Perry. Each needs a setting, a default, or a removal before the CLI works
in another repository:

| Assumption | Where | Note |
|---|---|---|
| The scanned directory is `journal/` | `SCAN_ROOT` in `rfc_lib.py`; hook scripts; `pre-commit`; link text in `render_status` | Other repos may use `docs/`, `rfcs/`, `adr/`. |
| Excluded files `CHANGELOG.md`, `STATUS.md` | `EXCLUDED_NAMES` | Make it a list setting. |
| Number floor 48 (next is 49) | `ID_FLOOR` | Perry-only reason (reserved legacy numbers). A new repo starts at 1. |
| Work-in-progress cap 3 | `IN_PROGRESS_CAP` | Setting. |
| The alias table | `ROLE_ALIASES` | Tuned to Perry's real headings by a corpus survey. A default set plus per-repo additions. |
| Required and expected roles per type | `REQUIRED_ROLES`, `EXPECTED_ROLES` | Relaxed on 2026-09-23 from Perry evidence. Keep them in the standard, not the repo config, unless a repo proves otherwise. |
| The interpreter path `venv/bin/python` | `check_status.sh`, hook scripts, `render_status` text, docstrings | A packaged CLI removes this: call `terrastep ...` instead. |
| The bare-`§` warning skips `spec §` | `BARE_SECTION_RE` | Comes from Perry's citation rule. Optional rule. |
| Migration heuristics | `propose_frontmatter.py`: `journal/CHANGELOG.md` path, `journal/v0-6/refactoring/` as the plan directory, Perry's status words | Keep the approach, make the paths settings. |
| Messages that name Perry files | `rfc_lib.py`, hooks, `check_claude_md*.sh` | Point them at terrastep's docs instead. |

## 6. Lessons that must carry over

Each one cost a round in Perry. The design note has the details.

- **Every rule ships with a negative control.** A test that starts from a passing fixture, changes one thing, and
  expects exactly that rule's code. Then disable the rule and watch a test go red. Two hook tests passed with their
  guard removed on the first attempt; only the sabotage run showed it.
- **Set the bar before seeing the data, and fix the format rather than the docs.** The first rule set passed 0 of 50
  real Perry docs. Four rule changes followed, each backed by a count from the corpus. Run `--survey` on any new
  corpus before trusting the alias table.
- **The migration guesses; the owner decides.** The first classifier was wrong on leading verdicts, negations,
  two status-line shapes, and changelog evidence. Reviewing the flagged rows before `--apply` caught it. Keep the
  propose, review, apply split.
- **Check what the commit will contain.** The pre-commit hook reads the index, not the working tree.
- **Keep the index deterministic.** No timestamp in `STATUS.md`, so `stale-index` means a real change.
- **Structure is checkable; reasoning is not.** The script cannot tell a weak recommendation from a strong one. That is
  the job of a review skill, not of more regexes.

## 7. Open and unverified

- **The four-week tests** in the design note ("What this does not show") are due from 2026-10-21, against Perry. The
  note says to keep or drop the format on that result. Do not freeze the standard before then.
- **The `Stop` hook in a live Claude Code session** has not been seen to block. Only the script was tested.
- **No `design` doc exists yet** in any real repository. The body rules have run only on fixtures
  and on in-memory copies of Perry docs.
- **Plugin, marketplace, copier, and Codex skill mechanics** in `teaching_repos_my_claude_method.md` were described from
  Claude's memory. Check current Claude Code plugin docs and current Codex docs (instruction files, skills) before
  designing the skill layer. That note also does not cover Codex at all.
- **Naming.** "TerraParse RFCs" (Perry), "terrastep" (this repo), "TerraParse Standardized Enhancement Proposals"
  (readme). Settle one term for docs, one for the CLI command, and one for the frontmatter or config key, early. Perry's
  docs and conventions say "TerraParse RFCs" and will need a pass when the name settles.
- **This directory is not a git repository yet.**

## 8. Suggested first steps

A suggestion, not a plan. The owner decides the order. Following the method, the first real act here should be a
`design` doc in terrastep's own format.

1. `git init`, commit this snapshot unchanged, so later diffs show what terrastep changed.
2. Write the first plan doc (number 1, since there is no legacy here) for the package: layout, CLI verbs, config
   file (for example `terrastep.toml` or a `[tool.terrastep]` table), and how Perry switches over. Use BQRS.
3. Package `rfc_lib.py` as the library, with the section 5 assumptions as configuration. Keep all 91 tests green and
   port them, including the hook tests.
4. Prove it on two corpora: Perry's `journal/` (expect the same 128 OK, byte-identical `STATUS.md`) and a second repo
   such as `~/dev/3p/tmdc-web`.
5. Then the skills: one to write a plan doc, one to review it, one to change status. They call the CLI. They do not
   re-implement rules.
6. Then the Perry switch: replace Perry's `scripts/` copies with the CLI, and add a dated note in Perry's design note.
