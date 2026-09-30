---
status: implemented
status_changed: 2026-09-28
type: plan
next: None. Sequencing steps 1-9 are done (see "What was built" below). Step 10 (the tmdc-web corpus, the skills doc, the Perry switch doc) is separate future work.
---

# Python package and CLI: layout, config, and moving the seed, tests and examples

**Status: IMPLEMENTED.** First terrastep design doc. It follows `journal/origin/handoff.md`, section 8, step 2.

## What this is, in one sentence

A plan to turn `seed/scripts/` into an installable Python package with one `terrastep` command, move `seed/tests/` to a root `tests/` directory, and file every item in `examples/` as a test fixture or a journal entry in `journal/origin/`. Nothing from `examples/` is kept as a standing reference past the port (see "Where each example goes").

## The problem, stated plainly

- **The prototype only works inside Perry's layout.** `rfc_lib.py` sets `REPO_ROOT` from its own file location and `SCAN_ROOT = "journal"`. The shell wrappers call `venv/bin/python scripts/...`. The handoff (section 5) lists ten such assumptions.
- **The logic is spread over seven scripts and three shell hooks.** Each script parses its own arguments. `check_status.sh` and `install_git_hooks.sh` only find the interpreter and call the next script.
- **The tests reach into `seed/`.** `test_rfc_check.py` and `test_propose_frontmatter.py` call `sys.path.insert(0, ".../scripts")`. `test_status_hooks.py` copies six script files into a temp git repo and writes a fake `venv/bin/python` there.
- **`seed/`, `examples/` and `journal/plans/` are untracked.** `git status` shows all three as `??`. Nothing records what was inherited unchanged.
- **terrastep's own journal fails its own check under today's `scan_dir = "journal"`.** Run today with `--root .`: `journal/origin/handoff.md` has no frontmatter (`fm-missing`), and `journal/STATUS.md` does not exist (`stale-index`). Under the `scan_dirs` design below (see Config), `journal/origin/` is no longer scanned, so this specific failure goes away on its own — see Sequencing step 2.

## The design

### Layout

```
pyproject.toml            package metadata, dependencies, the `terrastep` entry point
terrastep.toml            terrastep's own config (scan_dirs = ["journal/plans"])
src/terrastep/
  __init__.py, __main__.py
  cli.py                  argparse and verb dispatch. No rules.
  config.py               Config dataclass. Finds and loads terrastep.toml.
  core.py                 rfc_lib.py: parser, rules, render_status. Reads Config, not constants.
  migrate.py              propose_frontmatter.py
  hooks.py                pre-commit and "check if changed" logic
tests/
  conftest.py
  test_core.py            from seed/tests/test_rfc_check.py
  test_migrate.py         from test_propose_frontmatter.py
  test_hooks.py           from test_status_hooks.py
  test_cli.py             new: verbs, exit codes, config lookup
  fixtures/               from seed/tests/rfc_fixtures/, plus the two Perry docs
integrations/claude/      the Stop hook shim (see Q5)
examples/perry/           temporary: read once for fixtures and the Perry handoff document, then deleted (see "Where each example goes")
journal/plans/vX.Y/       the one designated directory (see Config): terrastep's own proposals, checked and built by the CLI
journal/origin/           inherited notes, not a designated directory: plain markdown, no frontmatter required
```

`core.py` stays one file at first. It holds the parser and every rule today (500 lines). A split needs a reason from a test or a change, not a guess. The first change to it is mechanical: constants become `Config` fields, with the old values as defaults.

### CLI verbs

| Verb | Functionality | Replaces | Notes |
|---|---|---|---|
| `terrastep check [FILES] [--if-changed]` | Reads each document's frontmatter under `scan_dirs` and reports a failure code per rule broken (`fm-missing`, `fm-status-type`, `stale-index`, ...), or OK if none are. | `check_status.py`, `check_status.sh` | Same output text and exit codes as today. `--if-changed` exits 0 with no output when the scan directory has no uncommitted change (used by the Stop hook). |
| `terrastep survey [DIR]` | Lists the documents under a directory and their frontmatter fields, without applying the pass/fail rules `check` applies. | `check_status.py --survey` | Its own verb, as the handoff table names it. |
| `terrastep build [--stdout]` | Regenerates `index_file` from the current frontmatter of every document under `scan_dirs`. | `build_status.py` | Writes the index file. |
| `terrastep next-id` | Reads existing document ids under `scan_dirs` and prints the next unused one, respecting `id_floor`. | `build_status.py --next-id` | |
| `terrastep migrate propose` / `migrate apply` | Reads a document with no frontmatter (or old-format frontmatter) and proposes new frontmatter for owner review; `apply` writes an already-reviewed proposal into the file. | `propose_frontmatter.py`, `--apply` | Keeps the propose, review, apply split. |
| `terrastep install-hooks` | Writes a git pre-commit hook that calls back into `terrastep hook pre-commit`. | `install_git_hooks.sh` | See "Hooks". |
| `terrastep hook pre-commit` | Checks the staged snapshot of `scan_dirs` and blocks the commit if it fails. | `git-hooks/pre-commit` | Called by the installed shim. |

Every verb takes `--root DIR` and `--config FILE`. The default root is the nearest parent directory that holds `terrastep.toml`, then the git root, then the current directory.

### Config

One file, `terrastep.toml`, at the repo root. Every key has a default. A repo with no file runs on defaults.

The standard applies only inside a list of designated directories, not to every markdown file in the repository. `terrastep check` and `terrastep build` only read a file if it sits under one of `scan_dirs` (recursively, including its version subdirectories). A markdown file outside every listed directory is not scanned, is not required to carry frontmatter, and is not listed in any `STATUS.md`. This repo's own `terrastep.toml` sets `scan_dirs = ["journal/plans"]`. By convention, each entry then holds version subdirectories (`v0.1/`, `v1.0/`, `v13.4.1/`, ...); the CLI does not enforce that naming, it only recurses.

| Key | Default | Replaces | Note |
|---|---|---|---|
| `scan_dirs` | `["journal"]` | `SCAN_ROOT` | A list, not a single path. Also used in index link text and hook guards. Each entry is scanned recursively, so version subdirectories under it are included. |
| `index_file` | `"STATUS.md"` | name in `EXCLUDED_NAMES` | Always excluded from the scan. |
| `exclude` | `["CHANGELOG.md"]` | `EXCLUDED_NAMES` | Extra names to skip. |
| `id_floor` | `0` | `ID_FLOOR = 48` | Next number is floor + 1. Perry sets 48. |
| `in_progress_cap` | `3` | `IN_PROGRESS_CAP` | Warning only, as today. |
| `[aliases]` | none | `ROLE_ALIASES` | Adds patterns to a role. Never removes a built-in one. |
| `warn_bare_section` | `false` | `BARE_SECTION_RE` | A bare section is a `§N` reference with no document named alongside it (e.g. `§8` instead of `handoff.md §8`), so a reader cannot tell which document's section 8 is meant. Warning only, never a failure. Perry's citation rule, so it is optional. |
| `[migrate] changelog` | none | `journal/CHANGELOG.md` in `propose_frontmatter.py` | |
| `[migrate] plan_dir` | none | `journal/v0-6/refactoring/` | |

`REQUIRED_ROLES`, `EXPECTED_ROLES`, the state list, the type list and the failure codes stay in code. They are the standard, not a repo choice (handoff, section 5).

### Hooks

- **Pre-commit.** The logic moves from bash to `hooks.py`. It still exports the staged snapshot with `git checkout-index` and checks that copy, not the working tree. `terrastep install-hooks` writes `.git/hooks/pre-commit`: one line, `exec "<interpreter>" -m terrastep hook pre-commit`. The interpreter path is the one that ran the installer. It refuses to overwrite an existing hook unless given `--force`.
- **Stop hook.** It stays a shell script in `integrations/claude/`, because it returns Claude Code's JSON (`{"decision": "block", ...}`) and reads Claude's `stop_hook_active` field. It calls `terrastep check --if-changed`. It keeps its `jq` dependency. Packaging it belongs to the later skills and plugin doc.
- **`check_claude_md*.sh`.** Deleted, not moved (see Q6). They guard one Perry regression (a dated narrative section landing in `CLAUDE.md` or `docs/conventions.md`), hardcoded to Perry's file names and paths. They test no part of the frontmatter/status format and don't belong in a repo meant to be independent of Perry.

### Where each seed file goes

| Seed file | Destination |
|---|---|
| `seed/scripts/rfc_lib.py` | `src/terrastep/core.py`, with `config.py` split out |
| `check_status.py`, `build_status.py` | `cli.py` verbs |
| `check_status.sh`, `install_git_hooks.sh` | deleted. The verbs replace them. |
| `propose_frontmatter.py` | `src/terrastep/migrate.py` |
| `git-hooks/pre-commit` | `hooks.py`, plus the generated shim |
| `check_status_stop_hook.sh` | `integrations/claude/stop_hook.sh` |
| `check_claude_md.sh`, `check_claude_md_hook.sh` | deleted. Perry-specific, not part of the format (Q6). |
| `seed/tests/*.py`, `rfc_fixtures/` | `tests/`, renamed as in the layout above |

`seed/` is empty after the move and is deleted.

### Where each example goes

One rule per destination:

1. **A test reads it: `tests/fixtures/`.**
2. **It records inherited history or the source text of the standard: `journal/origin/`**, with frontmatter, kept for consistency with the format even though `journal/origin/` is not a designated `scan_dirs` entry and so is not itself checked.
3. **Everything else is scaffolding for the port, not a kept reference.** It is read once, for the corpus run and the Perry handoff document (B2), then deleted with the rest of `examples/perry/`. Files that are not markdown, and files that would need fake frontmatter, are read the same way and deleted the same way.

| Example | Destination | Reason |
|---|---|---|
| `journal/resume_stage_shortcuts.md`, `s3_prefix_split.md` | `tests/fixtures/perry/` | The closest real BQRS docs. Tests use them for `survey` and for the check on `legacy` docs. Both keep `type: legacy`. |
| `journal/status_migration_proposal.md` | `journal/origin/perry_status_migration_proposal.md` | A record of a reviewed migration. It needs Perry's 126 docs to regenerate, so no test can use it. Its status changes from `implemented` to `closed` with reason `reference`, because a `note` may not be `implemented` (`fm-status-type`). |
| `conventions_method_excerpt.md` | `journal/origin/perry_conventions_method_excerpt.md` | The Perry wording of the rules. It is the source text for the standard. Added as `type: note`, `closed`, `reference`. |
| `journal/STATUS.md` | deleted with `examples/perry/` | A generated sample, read once for the `stale-index` case (B2). Not kept, since a frozen 128-doc snapshot would drift from Perry's real journal and become a fixture we test against in perpetuity. |
| `CLAUDE.md`, `claude_settings.json` | deleted with `examples/perry/` | Not kept as a template seed. A future `init` template is designed from terrastep's own requirements when that work starts, not preserved Perry files. |

A fixture must be read by at least one test. Anything in `examples/perry/` that is not promoted to a fixture or a `journal/origin/` note is read once — for the corpus run and the handoff document — then deleted, not kept as a standing example directory.

### Tests

- The 91 tests move and keep their count. The move is two commits: a rename with no content change, then the import and path changes. `git log --follow` then works.
- Tests import `terrastep`, not a `scripts/` path. `conftest.py` asserts that `terrastep.__file__` sits under this repo's `src/`. This stops a stale copy in `site-packages` from passing the tests (B1).
- `test_hooks.py` runs `python -m terrastep ...` with `sys.executable`. The fake `venv/bin/python` wrapper is gone, because the shim carries the interpreter path.
- `test_hooks.py` still skips when `git` or `jq` is missing. It no longer needs `python3` on `PATH`.

## What this does not do

- **It does not say how Perry switches to the package.** The mechanics and timing of the cutover are a separate design doc (the Perry switch doc, Sequencing step 10), written once the library is more stable. This plan only produces the handoff document that explains what changed and suggests compliance code (B2). Nothing here edits Perry's repository.
- **It does not build a general version-to-version migration tool.** The Perry handoff document's suggested code is hand-written for this one cutover. Automated migrations between terrastep's own released versions are future work, once terrastep has a version history to migrate between.
- **It does not design the skills, the plugin, the copier template or Codex support.** Section 5 of the handoff lists them as later work.
- **It does not write the standard as prose independent of the CLI.** `journal/origin/` only keeps the source text.
- **It does not renumber or migrate any Perry doc.**
- **It does not change a rule.** Failure codes, states, types and output text stay as they are.
- **It does not publish to PyPI.**

## Verification

- **Test count.** 91 tests pass after every sequencing step, not only at the end.
- **Negative controls, redone for the new code.** Config lookup, `--if-changed` and `hook pre-commit` are new code. Each gets a test that fails when the code is disabled. The sabotage loop from the design note (section 8, step 2) runs on them, with a `cmp` check after each restore.
- **Defaults equal the seed.** With `terrastep.toml` set to Perry's values (`id_floor = 48`, `warn_bare_section = true`, Perry's paths), the fixtures give the same findings as the seed did.
- **Own journal is clean.** `terrastep check` prints OK on this repo's `journal/plans/` (with `scan_dirs = ["journal/plans"]` in `terrastep.toml`), and `terrastep build` writes `journal/plans/STATUS.md`. `journal/origin/` is untouched, since it is not a designated directory.
- **Perry corpus, read only, once.** A one-time, opt-in run (not a permanent test) reads Perry's `journal/` and expects the 128 OK and a byte-identical `STATUS.md`, proving the port preserved behavior at cutover. It never writes to Perry and is not repeated as a standing check. See B2.

## Blockers

### B1 — A stale installed copy can pass the tests against old code [resolved]

The tests will import `terrastep`. If `venv/` holds a regular install from an earlier step, the tests import that copy and pass while `src/` has a bug. Nothing shows the mismatch.

**Recommendation:** install with `venv/bin/pip install -e .` only. Add the `conftest.py` assertion on `terrastep.__file__` (see Tests). Write the installer's interpreter path into the hook shim, so the shim and the tests use the same code.

### B2 — The Perry corpus is not in this repository, and should not become a standing dependency [resolved]

The handoff expects 128 OK and a byte-identical `STATUS.md` on Perry's journal. `examples/perry/` holds 4 of those docs. `examples/perry/journal/STATUS.md` lists 128, so a check against it fails `stale-index`. A test that skips when Perry is absent reports green with nothing proved.

Perry is this project's starting point, not its permanent oracle. terrastep's rules are meant to diverge from Perry's as this project's own requirements demand, so a permanent test that Perry's corpus must always pass 128/128 would pin terrastep to Perry's history instead of the other way around.

**Recommendation:**

- **Run the corpus comparison once, read only, opt-in**, through an environment variable (`TERRASTEP_PERRY_CORPUS=<path>`). It proves the port preserved today's behavior — 128 OK, byte-identical `STATUS.md` — at cutover. It never writes to Perry, and the 128 docs are never copied into this repository.
- **Don't keep it as a standing test.** This is a one-time, hand-run step in Sequencing (step 9), reported once, not a permanent `corpus`-marked pytest that future contributors must keep green against a Perry checkout they may not have. The docs already carried into `tests/fixtures/perry/` (see "Where each example goes") are the only lasting tie to Perry; from that point they are terrastep's own test data and change freely with terrastep's own rules, not Perry's.
- **Produce a handoff document for Perry's owner from the same run**: what changed between what terrastep inherited from Perry (`scan_dir` string → `scan_dirs` list, renamed config keys, the deleted `check_claude_md*.sh` hooks, new CLI verb names, ...) and what terrastep is now, plus concrete suggested code — a `terrastep.toml`, updated script/hook calls — to bring Perry's own journal into compliance. This fleshes out the "Perry switch doc" named in Sequencing step 10 and in "What this does not do." It documents Perry's repository, not this one, so it is not committed into terrastep's own `journal/`; Claude drafts it, the owner reviews and delivers it to Perry.
- **No automated migration tool yet.** The handoff document's suggested code is hand-written for this one cutover. A general path for migrating a repository from one terrastep version to the next is future work, once terrastep has released versions to migrate between (see "What this does not do").

### B3 — `seed/`, `examples/` and `journal/plans/` are untracked, so the move has no baseline [resolved]

`git status` shows all three as `??`. The repository has one commit and none of the three is in it. A `git mv` needs tracked files, and later diffs cannot show what terrastep changed.

**Recommendation:** the owner commits `seed/`, `examples/` and `journal/plans/` unchanged first (handoff, section 8, step 1). This is the first step in Sequencing. Claude does not commit.

## Questions

### Q1 — `src/` layout or a flat package?

The risk is not that tests read the working tree — an editable install of either layout still points straight back at those files, so tests run against current edits either way. The risk is *how* a test reaches that code, and whether the packaging metadata (`pyproject.toml`) gets exercised on the way there.

With a flat `terrastep/` next to `tests/` at the repo root, `pytest` inserts the repo root onto `sys.path` on its own. `import terrastep` in a test then resolves straight to that sibling directory, whether or not anyone ever ran `pip install -e .`. `pyproject.toml` could name the wrong package, drop the `terrastep` entry point, or exclude a file the package needs, and the tests would still pass, because they never went through the installer to find out. A real user running `pip install terrastep` would hit a broken install the test suite never caught.

`src/terrastep/` closes that gap: `src/` sits outside where `pytest`'s rootdir insertion looks, so `import terrastep` raises `ModuleNotFoundError` until the package is actually installed. That forces `pip install -e .` to run at least once, which reads `pyproject.toml` for real and builds the package the same way a real install would. This is a property of *declaring an installable package* — the same argument holds if this project used `setup.py`/`setup.cfg` instead of `pyproject.toml`; it has nothing to do with `pyproject.toml` versus `requirements.txt`, since `requirements.txt` never declares a package or an entry point in the first place, so it can't be installed via `pip install -e .` at all.

This is also the other half of B1: once `src/` forces every environment to run an install, B1's `conftest.py` assertion on `terrastep.__file__` catches the mirror-image bug — a *stale* install sitting in `site-packages` instead of the current `src/` edits. `src/` plus that assertion close both directions: accidental raw-path import (this question), and stale-install import (B1).

**Recommendation:** `src/terrastep/`.

### Q2 — Config in `terrastep.toml`, or in a `[tool.terrastep]` table of `pyproject.toml`?

The handoff names both. A repo like `tmdc-web` may have no `pyproject.toml`.

**Recommendation:** `terrastep.toml` only, for now. Read `[tool.terrastep]` later if a repo asks for it. Defaults are `scan_dirs = ["journal"]` and `id_floor = 0`, so a new repo needs no file for scan dirs. This repo overrides `scan_dirs` to `["journal/plans"]` (see Config).

### Q3 — Which Python floor?

The handoff says 3.11 or newer. The local `venv/` runs 3.10.12, and all 91 tests pass on it today. `tomllib` is standard only from 3.11.

**Recommendation:** floor 3.10, with `tomli` as a dependency when Python is older than 3.11 (`tomli; python_version < "3.11"`). Raise the floor when 3.10 reaches end of life (October 2026). Dependencies: `pyyaml`, plus that marker. `pytest` is a dev extra.

### Q4 — What names do the package, command, config file and documents use?

The handoff (section 7) asks for one term each. The prototype says "RFC" in `rfc_lib.py`, in output messages and in test names.

**Recommendation:** package, command and config file are all `terrastep` and `terrastep.toml`. A document is a "proposal" in messages. `rfc_lib.py` becomes `core.py` in this plan. Message text changes wait for the owner's final choice of term, because output text must stay identical until then.

### Q5 — Does the Stop hook live in the Python package?

It returns Claude Code's JSON and reads its `stop_hook_active` field. That is specific to one agent. The pre-commit hook is plain git.

**Recommendation:** no. `terrastep` owns `check --if-changed` and `hook pre-commit`. The Stop hook stays a shim in `integrations/claude/`. This keeps agent details out of the library, as the handoff's third goal asks.

### Q7 — Where does `STATUS.md` live when `scan_dirs` holds one directory?

With `scan_dirs = ["journal/plans"]`, `index_file` could sit at the repo-root `journal/STATUS.md`, listing every proposal across all version subdirectories, or at `journal/plans/STATUS.md`, directly inside the one designated directory. Perry's config keeps `scan_dirs = ["journal"]` (one entry, no version subdirectories), so its index stays at `journal/STATUS.md` either way; this only forks for a repo like this one whose designated directory is not the scan root's only content.

**Recommendation:** `index_file` is always written inside the (first, and today only) entry of `scan_dirs`, so here that is `journal/plans/STATUS.md`, not `journal/STATUS.md`. This keeps the index next to what it indexes and out of `journal/origin/`, which is not scanned. Revisit if a repo ever lists more than one `scan_dirs` entry, since one index per entry, or one merged index, is then an open choice.

### Q6 — Keep `check_claude_md*.sh` at all?

They enforce a Perry rule about `CLAUDE.md`, hardcoded to Perry's file names (`CLAUDE.md`, `docs/conventions.md`) and Perry's own incident (`claudemd_redesign.md`). The handoff calls them "a candidate for the standard", but nothing in them checks frontmatter, status, or any rule this project defines. terrastep's goal is to be the independent, robust format that Perry then conforms to, not a repository shaped by Perry's specific history. Keeping Perry-specific scripts here, even as an example, runs that dependency backwards.

**Recommendation:** no, delete them, do not port to `examples/perry/scripts/`. If a second repository later wants a "no dated narrative sections outside the journal" rule, design it as a general terrastep rule from that repository's own need, not by resurrecting Perry's script.

## Recommendations

1. Owner commits `seed/`, `examples/` and `journal/plans/` unchanged before any move (B3).
2. Install editable only, and guard with `conftest.py` (B1).
3. Run the Perry corpus comparison once, at cutover, not as a standing test; draft the Perry handoff document from that run, then delete `examples/perry/` (B2).
4. Use `src/terrastep/` (Q1).
5. Use `terrastep.toml` only (Q2).
6. Floor 3.10 with the `tomli` marker (Q3).
7. Name everything `terrastep`. Call a document a "proposal". Hold message text until the term is final (Q4).
8. Keep the Stop hook out of the package (Q5).
9. Delete the `CLAUDE.md` checks; do not port them to examples (Q6).
10. Write `index_file` inside the first `scan_dirs` entry, so this repo's index is `journal/plans/STATUS.md` (Q7).

## Sequencing

1. **Owner commits the snapshot** (B3).
2. **Fix terrastep's own journal.** Add a `terrastep.toml` with `scan_dirs = ["journal/plans"]`, so `journal/origin/handoff.md` is out of scope and needs no frontmatter (Q7). Run the seed's `check_status.py --root .` and `build_status.py --root .`, pointed at `journal/plans`, until they print OK. This proves the format on its own repo before any code moves.
3. **Add `pyproject.toml` and the editable install.** Add the `conftest.py` guard (B1).
4. **Move, no content change.** `git mv` the seed modules to `src/terrastep/` and the tests to `tests/`. Commit. Then fix imports and paths. 91 tests pass.
5. **Config.** Add `config.py` and replace the constants. Add Perry-values and default-values tests.
6. **CLI.** Add `cli.py` and the verbs. Delete the two shell wrappers. Add `test_cli.py`.
7. **Hooks.** Port pre-commit to `hooks.py`, add `install-hooks` and `check --if-changed`, move the Stop hook. Redo the negative controls.
8. **Examples.** Move each file by the table. Add frontmatter to the two origin notes. `terrastep check` on this repo prints OK. Delete `seed/`.
9. **Corpus run against Perry, read only, once** (B2). Report the result, including a skip. Draft the Perry handoff document from this run: what changed since terrastep inherited from Perry, and suggested code to bring Perry into compliance. Delete `examples/perry/` once its fixtures (step 8) and the handoff document's content are captured.
10. **Then** the second corpus (`tmdc-web`), the skills doc, and the Perry switch doc — the mechanics and timing of Perry's cutover, building on the handoff document from step 9. Each is its own design doc.

## What was built (2026-09-28)

Steps 1-9 done, each as its own commit on `dev`. Step 10 is out of scope here (separate future design docs).

- **Steps 1-2** (owner-committed snapshot; `terrastep.toml` with `scan_dirs = ["journal/plans"]`; `journal/plans/` checks clean under the seed scripts before any code moved).
- **Steps 3, 5, 6, 7, done together** (the modules are tightly coupled): `src/terrastep/{config,core,migrate,cli,hooks}.py`, installed editable via `pyproject.toml`. `tests/conftest.py` asserts `terrastep.__file__` sits under this repo's `src/` (B1). `core.py` is `rfc_lib.py` reworked to read a `Config` (list `scan_dirs`, `index_file` written inside the first entry per Q7, `warn_bare_section`/`aliases` config-gated) instead of module constants.
- **Step 4, folded into the above** rather than a separate no-content-change `git mv` commit: the seed modules were ported directly into their final `src/terrastep/` shape (renamed and reworked in the same commit as steps 3/5/6/7), not moved byte-identical first. `git log --follow` on the new files therefore starts at that commit, not at a pure rename — a divergence from the step-4 text above, accepted in exchange for not shipping an intermediate, not-yet-config-driven copy.
- **Step 8**: `examples/perry/` filed per the table — `tests/fixtures/perry/` (read by `tests/test_perry_fixtures.py`), `journal/origin/perry_*.md` (frontmatter added/corrected), the rest deleted. `seed/` deleted. `terrastep check` on this repo's `journal/plans/` prints OK.
- **Step 9**: run once, read-only, against the real Perry checkout (128 documents). Result: **21 pre-existing `fm-status-type` failures, not caused by the port** — confirmed by running Perry's own unmodified `rfc_lib.py`/`check_status.py` against the same corpus and diffing: identical 21 failures, identical (zero) warnings, identical `next_id` (49). The rendered index is byte-identical except two lines of tool-name text (`scripts/build_status.py` → `terrastep build`). The Perry handoff document (what changed, suggested `terrastep.toml`, a verb-by-verb replacement table, and the 21-failure finding) was drafted and handed to the owner outside this repository, per B2's recommendation not to commit it into terrastep's own `journal/`.
- **Test count**: 91 ported/adapted plus 14 new (`test_cli.py`: new per the plan; 4 added to `test_core.py` for the config surface; `test_perry_fixtures.py`: new) = 105, all passing throughout.

**Divergences from the plan as written**, both judgment calls made during implementation, not owner-approved in advance:
1. Step 4's separate "no content change" `git mv` commit did not happen; the mechanical move and the config rework landed together (see above).
2. `core.py`'s generated-index boilerplate text changed (`terrastep build` in place of `scripts/build_status.py`), because the old script no longer exists to name correctly. Q4 said to hold message text until the owner finalizes terminology; this one line could not stay literally accurate and be held at the same time, so correctness won. This is the sole source of the corpus run's non-byte-identical result (see step 9 above).
