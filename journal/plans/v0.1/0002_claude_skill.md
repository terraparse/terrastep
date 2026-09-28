---
status: planning
status_changed: 2026-09-28
type: design
next: Owner reviews. B1 to B4 need an owner decision before this moves to ready.
---

# A Claude Code skill for terrastep: generated from core.py, bundled with pip

**Status: PLANNING.** Second terrastep design doc. Follows the decisions reached in chat on
2026-09-28 (skill distribution and content-shape options), not a separate origin note.

## What this is, in one sentence

A plan to add a generator that produces `journal/terrastep_101.md` and a Claude Code skill from
`core.py`'s actual constants (one source of truth, not hand-written prose), bundle the skill as
pip package data, and add a `terrastep skill install` verb so adopting terrastep in a new repo is
two commands: `pip install terrastep`, `terrastep skill install`.

## The problem, stated plainly

- **`journal/terrastep_101.md` is hand-written prose that paraphrases `core.py`.** Nothing keeps
  the two in sync. A rule change in `core.py` (a new failure code, a changed alias) has no forcing
  function that updates the doc, and the doc already drifted once from the seed's `rfc_lib.py`
  docstrings before this project started reworking it.
- **An agent writing a `type: design` document today has to freehand the body shape from
  context alone.** The BQRS section order, the exactly-one `[open]`/`[resolved]` tag per blocker,
  the recommendation-coverage rule, the role-alias headings — all intricate, all easy to get
  subtly wrong without a reference in front of the model as it writes.
- **There is no way to get terrastep's Claude Code integration into a new repo except copying
  files by hand.** 0001 built the CLI and the hooks for this repo; nothing yet makes either
  available to a second repo. The stated goal (2026-09-28, chat) is per-repo opt-in that is
  "very easy to incorporate" once chosen — today that means manually recreating `terrastep.toml`,
  the pre-commit hook install, and (once it exists) the skill, from memory or by reading this
  repo's source.

## The design

### The generator

A new module, `src/terrastep/skilldoc.py`, reads `core.py`'s constants directly — `STATES`,
`NOTE_STATES`, `TYPES`, `PLAN_TYPES`, `CLOSED_REASONS`, `ROLE_ALIASES`, `REQUIRED_ROLES`,
`EXPECTED_ROLES`, `DECISION_NAMES`, and the failure-code registry (see B1) — and the `Config`
dataclass's field defaults from `config.py`. No new templating dependency: plain Python string
building, the same style `core.py`'s `render_status` already uses (see Q1).

It renders three things from one pass over that data:

1. **`journal/terrastep_101.md`**, replacing today's hand-written version. Same three-part shape
   (the format, the tools, how to use them) it already has; the "1. The format" and "2. The tools"
   sections become fully generated (they're just the constants above, formatted as tables), "3. How
   to use them" stays a short hand-authored set of example command sequences (the generator has no
   way to derive "here is a realistic workflow" from constants alone).
2. **`skill/SKILL.md`** — short and procedural, not the full reference (see "Content shape" below).
3. **`skill/references/format.md`** and **`skill/references/verbs.md`** — the exhaustive tables
   (failure codes, states/types, CLI verbs and flags), generated the same way as `terrastep_101.md`'s
   first two sections, loaded by the skill only when needed (progressive disclosure).

### Content shape: procedure first, reference on demand

`SKILL.md` opens with the decision procedure, not the spec:

- Writing a new `type: design` document: run `terrastep next-id`, scaffold the skeleton (frontmatter
  + the four decision sections in order), fill it in, run `terrastep check`, fix any failure using
  `references/format.md`'s code table, run `terrastep build`.
- Reviewing or fixing an existing document that fails `terrastep check`: read the failure code,
  look it up in `references/format.md`, apply the fix, re-check.
- Bringing existing undocumented markdown under the format: `terrastep migrate propose`, review,
  `terrastep migrate apply`.

This matches the chat decision to generate the skill "using a template based on
`terrastep_101.md`" — the generated `SKILL.md` and `terrastep_101.md` are two renderings of the
same underlying data (one procedural and short, one narrative and complete), not independent
documents that happen to agree today.

### The trigger, and why it can't be purely structural

Claude Code loads a skill by matching its frontmatter `description` against the task in the
system-reminder listing — a textual match, not a structural predicate. "Narrow but structural"
(the 2026-09-28 decision) therefore has to be split across two mechanisms:

- **The frontmatter `description` is narrow and textual**: it names concrete triggers — writing,
  reviewing, or checking a design/plan/proposal document, or a task that mentions terrastep,
  `scan_dirs`, or the BQRS shape — so the skill doesn't load for unrelated markdown (a README, a
  code comment).
- **The skill's own first instruction is the structural check**: once loaded, `SKILL.md` tells
  Claude to look for `terrastep.toml` and confirm the file it's about to write or check actually
  sits under one of `scan_dirs` before treating the format's rules as binding. A repo with no
  `terrastep.toml`, or a markdown file outside every `scan_dirs` entry, means the skill's rules do
  not apply — same as the CLI's own behavior (0001, Config section).

### Packaging: bundled with pip, installed on demand, opt-in per repo

The generated `skill/` directory ships as package data (`[tool.setuptools.package-data]` in
`pyproject.toml`), located at runtime with `importlib.resources` relative to the installed
`terrastep` package — the same principle 0001's B1 guard relies on: the files travel with
whichever `terrastep` is actually installed, editable or not, never a separate copy that can go
stale against the code.

A new verb, `terrastep skill install [--force]`, copies that bundled `skill/` directory to
`.claude/skills/terrastep/` in the target repo, refusing to overwrite an existing one unless
`--force` — the same shape as `install-hooks` (0001), for one consistent "how terrastep verbs that
write files behave" convention. Because `.claude/skills/` is typically committed, running this
once per repo is also what makes the skill available to anyone else who clones that repo — the
opt-in decision is made once, by whoever runs the command, not by every person who checks the repo
out.

This directly answers the stated goal: an individual decides, per repo, whether to adopt
terrastep — nothing here makes the skill available anywhere it wasn't explicitly installed — and
once decided, adoption is `pip install terrastep && terrastep skill install`, no file copying by
hand.

### Complementary to, not a replacement for, the hooks

The pre-commit hook and the Stop hook (0001) are reactive: they catch a bad document at commit
time or turn-end. The skill is proactive: it aims to make the document correct before either hook
would ever have to fire. `SKILL.md`'s procedure explicitly closes the loop — after editing a
scanned document, run `terrastep check` and fix any failure before finishing the turn — rather
than leaving that entirely to the Stop hook to catch. Neither replaces the other: a human editing
a document outside a Claude Code session still needs the git hook; an agent that forgets to
consult the skill is still caught by both hooks before the bad document reaches history.

## What this does not do

- **It does not publish terrastep to PyPI or make its GitHub repository public.** Both are
  prerequisites for the easiest form of `pip install terrastep` across machines, but neither is a
  code change this plan makes.
- **It does not build a plugin-marketplace distribution path.** The 2026-09-28 decision was
  project-level + pip-bundled, not a separately-versioned plugin; that option stays available
  later if a team wants central management across many repos at once.
- **It does not enforce a version match between an installed skill and the `terrastep` CLI it
  describes.** The generated `SKILL.md` records which version produced it (Q5); actually detecting
  and warning on a mismatch is future work, the same way 0001 deferred a general migration tool.
- **It does not change any format rule.** Every constant the generator reads already exists in
  `core.py`; this plan only makes them legible to an agent and a new reader, in two renderings of
  the same data.
- **It does not install the skill into Perry, tmdc-web, or any other repository.** That's each
  repo's own opt-in decision, made by running the verb this plan adds — not a step in this plan.

## Verification

- **Generated `terrastep_101.md` matches a hand-reviewed baseline.** The first read of the
  generator's output is compared line by line against today's hand-written version; any content
  difference is either an intentional fix (the hand-written version already had a stale example) or
  a bug in the generator, not silently accepted.
- **A staleness test** (`tests/test_skilldoc.py`) regenerates `terrastep_101.md` and `skill/*` into
  a temp directory and asserts the result matches what's checked in — the same `stale-index`
  pattern `core.py` already applies to `STATUS.md`, applied here to the generated docs instead, so
  a `core.py` rule change without a regenerate fails the test suite, not just goes unnoticed.
- **`terrastep skill install` produces a skill Claude Code actually loads.** Run once in a scratch
  repo, then confirmed by hand in a Claude Code session (this can't be driven from `pytest`, since
  it depends on the harness's own skill-loading, not on terrastep's code).
- **Dogfooding**: run `terrastep skill install` on this repo itself once B1-B4 are resolved, and
  use it for 0003 (or whatever comes next) to see whether the generated procedure actually holds up
  writing a real document.

## Blockers

### B1 — Failure codes are scattered string literals, not an enumerable registry [open]

Every rule in `core.py` constructs `Finding("code-name", "message")` inline (e.g.
`Finding("fm-missing", "no frontmatter block...")`, more than twenty call sites across
`check_frontmatter` and `check_body`). The generator needs a complete, accurate list of every code
and what it means to render `references/format.md`'s table — grep-parsing `Finding(` calls out of
source is fragile (a call site could be reformatted, wrapped, or built dynamically without notice).

**Recommendation:** add a small `FAILURE_CODES: dict[str, str]` registry near the top of `core.py`
— code to one-line description — read by the generator directly. Existing `Finding(...)` call
sites are unchanged (they keep constructing findings inline); a new test asserts every code string
that appears in `core.py`'s source is a key in `FAILURE_CODES` and vice versa, so the registry
cannot silently drift from the call sites without failing the suite. This is deliberately the
smallest change that makes the codes enumerable — not a refactor of every call site to reference
the registry.

### B2 — Skill frontmatter can't express "only when the file is under scan_dirs" [open]

Claude Code's skill-loading matches a textual `description`, not a structural predicate. Left
unaddressed, the skill either over-triggers (loads for any markdown-writing task, including repos
or files with no relation to terrastep) or the "only when actually governed by terrastep" check
gets silently skipped by an agent that doesn't think to look for `terrastep.toml`.

**Recommendation:** split the two concerns, as in "The trigger" above — a narrow textual
`description` decides whether the skill loads at all; the skill's own first instruction, once
loaded, is to check for `terrastep.toml` and `scan_dirs` membership before applying any rule. This
puts the structural check inside the procedure the skill teaches, not inside the trigger
mechanism, which is the only place Claude Code actually runs code before deciding to load
something.

### B3 — Bundling package data and finding it reliably at runtime, across editable and regular installs [open]

`terrastep skill install` needs to locate its own bundled `skill/` directory regardless of whether
`terrastep` was installed with `pip install -e .` (files under `src/terrastep/`) or a regular
install (files under `site-packages/terrastep/`) — the same editable-vs-regular distinction 0001's
B1 guarded for imports, now for data files instead of code.

**Recommendation:** declare `skill/**` under `[tool.setuptools.package-data]` in `pyproject.toml`,
and locate it at runtime with `importlib.resources.files("terrastep") / "skill"`, never a path
computed from `__file__` assumptions about the install layout. Add a test that runs `terrastep
skill install` against both an editable and a built-wheel install of the package in a temp venv,
confirming both locate the same files.

### B4 — Nothing forces a regenerate before commit or release [open]

`core.py` can change (a new failure code, a changed alias) without anyone remembering to re-run
the generator, leaving `terrastep_101.md` and the bundled skill stale relative to the code that
actually enforces the rules — the exact problem this plan exists to close, reopened at the
generation step instead of the hand-writing step.

**Recommendation:** the staleness test in Verification is the primary guard (CI/`pytest` catches
it, same as `stale-index` does for `STATUS.md`). Add a `terrastep skill build` maintainer verb
(not part of the guidance a consuming repo would use — it regenerates the source files in *this*
repo) so fixing a caught staleness failure is one command, not manual reconstruction.

## Questions

### Q1 — Templating approach: plain string building, or a templating dependency (e.g. Jinja2)?

`render_status` in `core.py` already builds markdown with plain f-strings and list-joining; adding
Jinja2 would be the project's first templating dependency, for output that's simple tables and
lists.

**Recommendation:** plain Python string building, matching `render_status`'s existing style and
keeping the dependency list unchanged (`pyyaml`, plus the `tomli` marker — see 0001 Q3). Revisit
only if the templates grow complex enough that string-building becomes hard to read.

### Q2 — Does `terrastep skill install` overwrite unconditionally, refuse-unless-force, or diff-aware merge?

**Recommendation:** refuse unless `--force`, exactly matching `install-hooks` (0001). One
"terrastep verbs that write files into your repo are conservative by default" convention across
the whole CLI, rather than a special case for the skill.

### Q3 — Should generated files carry a "do not edit by hand" marker, like `STATUS.md` does?

**Recommendation:** yes. `terrastep_101.md`, `SKILL.md`, and both `references/*.md` files open with
the same `<!-- GENERATED by \`terrastep skill build\`. Do not edit by hand. -->` comment style
`render_status` already uses for `STATUS.md`, for the same reason: a hand edit to a generated file
is invisible until the next regenerate silently discards it.

### Q4 — Does the skill cover only document-writing, or the full workflow (migrate, hooks)?

**Recommendation:** the full workflow, matching `terrastep_101.md`'s existing "3. How to use them"
section — writing a new document, fixing a failing one, migrating existing undocumented markdown,
and installing the hooks. The skill's purpose is easing adoption end to end, not just easing
document-writing once someone has already set everything else up by hand.

### Q5 — Should the generated skill record which terrastep version produced it?

**Recommendation:** yes, a generated comment or frontmatter field carrying the installed
`terrastep.__version__` at generation time. This doesn't yet enable mismatch *detection* (out of
scope, see "What this does not do") — it only makes a future mismatch-checking feature possible
without regenerating every already-installed skill first.

## Recommendations

1. Add a `FAILURE_CODES` registry in `core.py` plus a source-consistency test, without touching
   existing `Finding(...)` call sites (B1).
2. Split the trigger: a narrow textual `description`, plus a `terrastep.toml`/`scan_dirs` check as
   the skill's own first instruction (B2).
3. Locate bundled skill files with `importlib.resources`, declared via `package-data`; test both
   editable and built-wheel installs (B3).
4. Rely on a staleness test as the primary guard against drift, backed by a `terrastep skill build`
   maintainer verb for fixing it (B4).
5. Plain Python string building for the generator; no new templating dependency (Q1).
6. `terrastep skill install` refuses to overwrite unless `--force`, matching `install-hooks` (Q2).
7. Every generated file opens with a "do not edit by hand" comment (Q3).
8. The skill covers the full workflow — writing, fixing, migrating, hooks — not just document
   authoring (Q4).
9. Record the generating `terrastep` version in each generated skill file (Q5).

## Sequencing

1. **`FAILURE_CODES` registry + consistency test** (B1). No behavior change; makes the codes
   enumerable.
2. **`skilldoc.py`**: read `core.py`/`config.py` constants, render `journal/terrastep_101.md`.
   Compare by hand against today's version (Verification); commit.
3. **`SKILL.md` + `references/*.md`**: the procedural skill content, the trigger-check instruction
   (B2), the hook-complementarity note, all rendered from the same generator pass. Hand-write the
   short workflow examples (Q4) once; the generator doesn't touch them on regenerate.
4. **Package the `skill/` directory as package data** (B3); `importlib.resources` lookup; tests
   against both an editable and a built-wheel install.
5. **`terrastep skill install [--force]`** verb (Q2), mirroring `install-hooks`.
6. **`terrastep skill build`** maintainer verb, plus the staleness test comparing checked-in
   generated files against a fresh run (B4).
7. **Dogfood**: `terrastep skill install` on this repo; confirm by hand that Claude Code loads and
   uses it correctly on a real document-writing task.
8. **Later, each its own decision**: installing the skill into Perry and tmdc-web; publishing
   terrastep publicly (PyPI, public GitHub); a plugin-marketplace distribution path, if ever
   needed.
