# terrastep 101

A plain explainer, not a proposal: it carries no frontmatter on purpose, because it does not sit
in a designated `scan_dirs` directory. See "1. The format" below for what that means.

## 1. The format

terrastep is a frontmatter-and-body convention for planning documents (design docs, proposals,
notes), plus a CLI that checks a repository against it. It does not apply to every markdown file
in a repository — only to files inside directories you name in `terrastep.toml`. Everything else
is ordinary markdown, free to look however you like.

### Frontmatter

Every scanned document opens with a YAML block:

```yaml
---
status: planning
status_changed: 2026-09-27
type: design
next: Owner reviews. B1 to B3 need an owner decision before this moves to ready.
---
```

| Field | Meaning |
|---|---|
| `status` | One of `planning`, `ready`, `in-progress`, `implemented`, `closed`. |
| `status_changed` | A `YYYY-MM-DD` date: when `status` last changed. |
| `type` | `design` (a proposal, numbered, the only type that gets the full body-shape check below), `legacy` (an inherited document, exempt from the body check), or `note` (a record, not a proposal — see below). |
| `next` | Free text: what happens next, or who's blocking it. |
| `closed_reason` | Required when `status: closed`: one of `superseded`, `rejected`, `withdrawn`, `reference`. |
| `blocked_by` / `superseded_by` | Optional: the filename of another scanned document. |

A `note` is never `planning`, `ready`, or `implemented` — only `in-progress` or `closed`. It's not
a proposal working toward a decision, so those states don't apply to it (rule `fm-status-type`).

A `design` document needs a number: the filename starts `NNNN_` (e.g. `0001_python_package_and_
cli.md`). Find the next free number with `terrastep next-id`.

### The body, for `type: design`

Only `design` documents get the body-shape check (`legacy` and `note` are exempt). The shape:

1. **Front matter sections** (prose, before the decision sections). At least one of `summary` or
   `motivation` is required and must be non-empty; `design` and `scope` are expected (a missing
   one only warns). Headings are matched to a role by a fixed alias table — `## What this is`
   matches `summary`, `## Why, in the terms...` matches `motivation`, and so on. An unrecognized
   heading just warns as "unclassified"; it never fails.
2. **Exactly four decision sections, in this order, nothing else between them**:
   `## Blockers`, `## Questions`, `## Recommendations`, `## Sequencing`. Missing one, having two,
   or having them out of order all fail (`body-order`).
   - **Blockers** and **Questions** each hold items: a bold run-in or `###` heading starting
     `B1`, `B2`, ... or `Q1`, `Q2`, .... A section with no items must instead say "None" with a
     reason (`body-empty`). Every blocker needs exactly one `[open]` or `[resolved]` tag on its
     first line (`body-tag`). Every item (except a `[resolved]` blocker) needs a recommendation:
     a `**Recommendation...` run-in, or the arrow form `→ **answer**` (`body-recommend`).
   - **Recommendations** must mention every still-open blocker/question by its id (`B2`, `Q1`,
     ...); order is a hint only, never a failure (`body-r-cover`).
   - **Sequencing** just needs to exist.
3. **After Sequencing**, any further section must carry a `YYYY-MM-DD` in its heading (e.g.
   `## What was built (2026-09-28)`) — undated trailing prose fails (`body-dated`).
4. **Status gates the body**: `status: ready` or `in-progress` with any `[open]` blocker fails
   (`gate-open-blocker`). `status: implemented` needs a section whose heading matches the
   `history` role (`## What was built`, `## Implementation record`, ...) (`body-history`).

### The index file

Each designated directory's first entry gets a generated `STATUS.md` (or whatever `index_file`
names): every scanned document, its status, newest change first, split into Active / Planning /
All / No-frontmatter-yet. Nobody edits it by hand — `terrastep check` fails (`stale-index`) if it
doesn't match what `terrastep build` would write.

### The full list of failure codes

`fm-missing`, `fm-yaml`, `fm-type`, `fm-status`, `fm-status-type`, `fm-date`, `fm-closed-reason`,
`fm-link`, `fm-id`, `fm-id-dup`, `body-order`, `body-roles`, `body-empty`, `body-items`,
`body-tag`, `body-recommend`, `body-r-cover`, `body-dated`, `gate-open-blocker`, `body-history`,
`stale-index`. Warnings (never fail a run): unclassified sections, out-of-order Recommendations
mentions, more `in-progress` documents than `in_progress_cap`, a bare `§N` citation (only if
`warn_bare_section` is on).

## 2. The tools

One installed command, `terrastep`, with these verbs:

| Verb | Does |
|---|---|
| `terrastep check [FILES] [--if-changed]` | Checks every document under `scan_dirs` (or just `FILES`, with context from all of them). Exits 1 on any failure. `--if-changed` exits 0 silently when nothing under `scan_dirs` is uncommitted — built for hooks, not humans. |
| `terrastep survey [DIR ...]` | Read-only: how every heading in the corpus classifies. Useful for tuning the alias table or auditing a new corpus before turning `check` on. |
| `terrastep build [--stdout]` | Regenerates the index file from current frontmatter. `--stdout` previews without writing. |
| `terrastep next-id` | Prints the next free `design` document number. |
| `terrastep migrate propose` / `migrate apply` | For documents with no frontmatter yet: `propose` writes a guessed-frontmatter table (touches no document) for you to review and edit; `apply` reads the reviewed table back and prepends the frontmatter, refusing any doc that already has some. |
| `terrastep install-hooks [--force]` | Writes `.git/hooks/pre-commit`, which runs `terrastep hook pre-commit` on every commit. Refuses to overwrite an existing hook unless `--force`. |
| `terrastep hook pre-commit` | What the installed hook calls: checks the **staged snapshot**, not the working tree, so an unstaged fix can't hide a bad commit. |

Every verb takes `--root DIR` and `--config FILE`; both default to auto-detection (nearest parent
holding `terrastep.toml`, then the git root, then the current directory).

### Config: `terrastep.toml`

One file, repo root, every key optional:

```toml
scan_dirs = ["journal/plans"]   # default: ["journal"]. The designated directories, and only them.
index_file = "STATUS.md"        # default. Written inside scan_dirs[0].
exclude = ["CHANGELOG.md"]      # default. Extra filenames to skip, on top of index_file.
id_floor = 0                    # default. Next design number is floor + 1.
in_progress_cap = 3             # default. Warning only.
warn_bare_section = false       # default. A `§N` reference with no document named.

[aliases]                       # adds heading patterns to a role; never removes a built-in one
# design = ["proposed shape"]

[migrate]
changelog = "journal/CHANGELOG.md"     # optional: propose finished status for docs it links
plan_dir = "journal/v0-6/refactoring/" # optional: docs here default to type: legacy
```

`scan_dirs` is the one setting that matters most: only files under a listed directory (recursively)
are ever touched by `check`, `build`, or the hooks. A markdown file anywhere else in the repo —
this file included — is invisible to terrastep.

### Hooks

- **Pre-commit** (`terrastep install-hooks`): blocks a commit whose staged `scan_dirs` snapshot
  fails `terrastep check`. `git commit --no-verify` bypasses it, same as any git hook.
- **Claude Code Stop hook** (`integrations/claude/stop_hook.sh`): before a session ends, runs
  `terrastep check --if-changed` and blocks the stop (returning Claude Code's
  `{"decision": "block", ...}` JSON) if it fails. Silent when nothing under `scan_dirs` changed,
  and never loops (`stop_hook_active` short-circuits it).

## 3. How to use them

**Starting a new proposal:**

```
terrastep next-id                         # → 0002
# write journal/plans/v0.1/0002_my_proposal.md, type: design, status: planning
terrastep check                           # confirm it passes
terrastep build                           # regenerate the index
```

**Day to day:** `terrastep install-hooks` once per clone; after that, the pre-commit hook and (in
a Claude Code session) the Stop hook keep the index and every document's frontmatter honest
without you thinking about it. Run `terrastep check` by hand any time to see the full picture, and
`terrastep build` after editing any document's `status`.

**Bringing an existing pile of undocumented markdown under the format:**

```
terrastep migrate propose     # writes a proposal table under scan_dirs[0]; touches nothing else
# review the table by hand — it's only a guess, and flags weak ones
terrastep migrate apply       # prepends the reviewed frontmatter; refuses any doc that already has some
terrastep build && terrastep check
```

**Bringing a new repository under the format for the first time:** write a `terrastep.toml` naming
`scan_dirs`, run `terrastep migrate propose`/`apply` on what's there already, then
`terrastep install-hooks`.
