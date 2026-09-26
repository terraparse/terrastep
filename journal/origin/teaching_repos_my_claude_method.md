---
status: in-progress
status_changed: 2026-09-25
type: note
next: Part 2 (rollout by plugin and copier template) is not started. It waits for the TerraParse RFC format to be committed and to run for four weeks.
---

# Teaching repos my Claude method — a status table, a standard for proposals, and a way to roll the method out

**Status: PLANNING. Nothing below is implemented.** Written 2026-09-23 from a
chat with Claude, for the project owner to come back to. Claude's knowledge
stops at January 2026, and the outside standards below are described from
memory. Check each one against its current docs before building on it.

Two questions started this note:

1. How do I track the status of many feature ideas (idea, planning, in
   progress, implemented) in one place I can read at a glance?
2. How do I teach every repo, old and new, my current way of working with
   Claude — and change that way later without redoing each repo by hand?

**Update 2026-09-23:** Parts 1 and 3 are now covered more fully in
`status_and_terraparse_rfcs.md`, which names the format "TerraParse RFCs." Their
text stays here as first written. This note remains the home of the rollout
question (Part 2). Where the two disagree on status or RFC details, the newer
note wins.

A third question came after: which widely used standard is closest to my own
proposal style (BQRS: Blockers, Questions, Recommendations, Sequencing)?

## Part 1 — The status table

### What exists today

40 of the 50 docs in `journal/v0-6/refactoring/` already start with a
`**Status: ...**` line. The words are free text ("PLANNING", "IMPLEMENTED AND
APPLIED", "MEASURED AND CLOSED", "SUPERSEDED", "REFERENCE"). The data exists.
It has no fixed vocabulary, and no file collects it.

`journal/CHANGELOG.md` lists completed changes only. It cannot show an idea
that has not shipped.

### Models this borrows from

- **PEP 0.** A Python Enhancement Proposal (PEP) keeps its status in its own
  header. The index, PEP 0, is generated from those headers. Nobody edits it by
  hand. Kubernetes Enhancement Proposals (KEPs) work the same way.
- **Architecture Decision Records (ADRs).** Each record carries a status with
  a short lifecycle: proposed, accepted, superseded.
- **Kanban.** A few flow states, and a limit on work in progress (WIP).

### Design

1. **The doc is the single source of truth.** Each design doc gets a small
   frontmatter block: `status`, `status_changed` (a date), and `next` (one
   line: the next action, or what blocks it).
2. **A script generates `journal/STATUS.md`.** It sorts by `status_changed`,
   newest first. An "Active" block sits on top with the `ready` and
   `in-progress` items. The full list follows. When I return cold, the Active
   block answers "what is in flight."
3. **A check script fails on a missing or unknown status.** It works like
   `scripts/check_claude_md.sh`. A written rule drifts. A failing check does
   not.
4. **Every idea gets a file.** A five-line stub is enough. An idea with no
   file is not tracked.

### Vocabulary

| State | Meaning | Word used today |
|---|---|---|
| `idea` | Stub only, no plan | none |
| `planning` | A BQRS doc exists, not yet approved | PLANNING, PROPOSAL |
| `ready` | Approved, not started | none |
| `in-progress` | Code is being written | none |
| `implemented` | Merged and applied | IMPLEMENTED AND APPLIED |
| `closed` | Ended without shipping. Give a reason: `superseded`, `rejected`, `withdrawn`, or `reference` | SUPERSEDED, MEASURED AND CLOSED, REFERENCE |

"Blocked" is a flag with a reason in `next`. It is not a state. Cap
`in-progress` at two or three items. The generated table warns when the cap is
exceeded.

The changelog stays as the record of completions. Later, it could become a
filtered view of the `implemented` rows. Do not do that yet.

### Migration

A one-time script maps the 40 existing status lines to the new vocabulary. It
flags the ambiguous ones for the owner to decide. Nothing is committed until
the owner approves the mapping.

## Part 2 — Teaching repos the method

There is no settled best practice yet. Three ideas keep appearing:

- Different kinds of content need different distribution. Copy nothing by
  default.
- Keep the always-loaded context small. Task-specific rules go into skills,
  which load on demand.
- Enforce hard rules with hooks and scripts, not prose.

### Three layers

| Layer | Holds | How it reaches a repo |
|---|---|---|
| **A. Personal** | `~/.claude/CLAUDE.md`: writing style, sound alerts, harness notes | Already works. Stays on this machine |
| **B. The method** | BQRS, the review discipline, changelog and status conventions, check scripts | A separate repo, `claude-method`, used two ways (below) |
| **C. Project-specific** | `architecture_map.md`, `known_gaps.md`, module `CLAUDE.md` files | Never synced |

**Layer B, way 1: a plugin (referenced, not copied).** Behavior lives in a
Claude Code plugin: skills such as `bqrs-plan`, `review-planning-doc`,
`status-update` and `changelog-entry`, plus slash commands and hooks. A plugin
marketplace can be a plain git repo. Each project installs by reference, and
an update reaches all projects. BQRS and the run-story genre are task-specific,
so they are skill candidates. Root `CLAUDE.md` would keep a one-line pointer to
each, as a guard against a skill failing to trigger. This is optional:
`docs/conventions.md` is always loaded by deliberate choice.

**Layer B, way 2: a copier template (copied, but updatable).** Some files must
live inside the repo: the `CLAUDE.md` skeleton, the `journal/` layout,
`STATUS.md` and its script, the `check_*.sh` scripts, and a baseline
`.claude/settings.json`. Use [copier](https://copier.readthedocs.io).
`copier copy` starts a new repo. `copier update` brings an old repo forward with
a three-way merge that keeps local edits, and records the template version in
`.copier-answers.yml`. Cookiecutter cannot update after generation, so copied
scaffolding drifts.

**Rejected:**
- Git submodule. It pins a version, but it is awkward to edit and to update.
- Symlink. It breaks in CI, in cloud sessions, and on other machines.
- Importing files from `~/` with `@`. It works for one person on one machine.
  It does not travel.

### Handling change over time

- The method has a version number. Release tags in `claude-method` carry it.
- `MIGRATIONS.md` in the method repo lists, per release, what changed and what
  to do. Example: "v3: `STATUS.md` replaces the top of `known_gaps.md`."
- An `adopt-method` skill reads the migration notes and applies them to the
  current repo. Copier does the mechanical part. Claude does the fuzzy part,
  such as normalizing the 40 status lines. Repos diverge, so this part needs
  judgment.
- New repo: `copier copy`, install the plugin, run `/adopt-method`.

## Part 3 — A standard for feature proposals

### The question

BQRS is a personal style. Which widely used standard is closest, and how does
it work with `STATUS.md`?

### Recommendation

**Adopt the lightweight-RFC family as the wrapper, and keep BQRS as the
body.** Request for Comments (RFC) processes here means the Rust RFC process
and the Kubernetes Enhancement Proposal (KEP) process. The KEP template has 25
  sections, so this note borrows its lifecycle and metadata, not its body. No single standard
matches BQRS. Standards split into two parts: a *wrapper* (a lifecycle, a
header with metadata, an index) and a *body* (the sections of the proposal).
The RFC family is the closest fit on both parts.

### Why this family fits

- **The body already overlaps.** The Rust RFC template has a required
  "Unresolved questions" section and a "Drawbacks" section. KEP has "Risks and
  Mitigations" and open questions. BQRS is the same material, made stricter:
  it splits blockers (a wrong answer gives a quietly incorrect system) from
  questions (any answer works), and it forces a recommendation on every item.
  Adopting the RFC family costs no change to BQRS.
- **The wrapper is what BQRS lacks.** A KEP keeps machine-readable metadata
  (`kep.yaml`) and a generated index. That is the mechanism proposed in Part 1
  in teaching_repos_my_claude_method.md. It is proven at scale.
- **The lifecycles map closely.** KEP statuses are `provisional`,
  `implementable`, `implemented`, `deferred`, `rejected`, `withdrawn` and
  `replaced`. **Verified 2026-09-23** against `kep.yaml` in
  `keps/NNNN-kep-template/` of kubernetes/enhancements (the README does not list
  them; the list is a comment on the `status` field in that YAML file). The same
  file has a separate `stage: alpha|beta|stable` field for maturity in the
  current release cycle. The fetch went through a summarizing tool, so re-read
  the raw file before copying the exact wording.

| This note's state | KEP status | Note |
|---|---|---|
| `idea` | `provisional` | KEP has no separate stub state |
| `planning` | `provisional` | |
| `ready` | `implementable` | |
| `in-progress` | `implementable` | KEP tracks progress in the separate `stage` field, not in the status |
| `implemented` | `implemented` | |
| `closed` (superseded) | `replaced` | Add a `superseded_by` field |
| `closed` (rejected, withdrawn, reference) | `rejected`, `withdrawn` | KEP also has `deferred`. Use `closed` with reason `deferred` if needed |

`in-progress` is the one state this note keeps that KEP does not. Kanban
supplies it, and the WIP cap needs it.

### Standards considered and not chosen

- **Architecture Decision Record (ADR), including the MADR template.** One
  decision per document. A BQRS doc holds many decisions. ADR is too small for
  a whole proposal. It is a good fit for one decided blocker (see the open
  question below).
- **Shape Up pitch (Basecamp).** Its "rabbit holes" resemble blockers. But
  the process is built around fixed time cycles and a team betting table. A
  solo developer gets little from that part.
- **Google-style design doc.** Similar body, no lifecycle or index. It supplies
  neither part of what is missing.
- **PEP.** The wrapper is right, but the process is built for public review
  and is heavier than needed.

### How it works with STATUS.md

1. **Frontmatter is the wrapper.** Every proposal starts with the block from
   Part 1: `status`, `status_changed`, `next`. Add `superseded_by` (a filename)
   and `blocked_by` (a filename). The existing docs already open with a status
   line and a context paragraph, so this replaces that line and adds nothing
   else.
2. **BQRS stays exactly four sections.** Convention says a BQRS doc has
   exactly four sections. The RFC "summary" and "motivation" go in the
   opening paragraph, not in new sections. Non-goals go there too.
   **Corrected 2026-09-23 in `status_and_terraparse_rfcs.md`:** this was too
   literal. Existing plans carry explanatory sections before the four decision
   sections. See "The body" and Q7 there.
3. **The blockers section gates promotion.** A doc may move from `planning` to
   `ready` only when every blocker is resolved. The check script enforces
   this. It needs a machine-readable marker on each blocker heading, such as
   `[open]` or `[resolved]`. The script fails when `status` is `ready` or
   `in-progress` and an `[open]` blocker remains. This ties the status table
   to the project's own definition of "quietly incorrect."
4. **The sequencing section feeds `blocked_by`.** When the Sequencing section
   says "must land after X," record X in `blocked_by`. `STATUS.md` shows a
   blocked row with its blocker's name.
5. **`next` stays hand-written.** One line. The script does not derive it.

## Open decisions, with recommendations

- **Q1. Use `[open]`/`[resolved]` tags on blocker headings, or a frontmatter
  counter (`open_blockers: N`)?** Recommend the tags. A counter in frontmatter
  is a second copy of a fact the body already states. This project has shipped
  a written-but-unread value a dozen times. The script counts the tags, so
  nothing can drift.
- **Q2. Record each decided blocker as an ADR?** Recommend no, for now. It
  doubles the file count, and a resolved blocker already sits in its design
  doc with its reasoning. Revisit if a decision needs a home outside its
  proposal.
- **Q3. Cap `in-progress` at two or three?** Recommend three, as a warning and
  not a failure. Measure how often the cap trips before making it strict.
- **Q4. Where does the status script live before `claude-method` exists?**
  Recommend `scripts/build_status.py` and `scripts/check_status.sh` in Perry,
  next to `check_claude_md.sh`. They move into the template later.
- **Q5. Should the changelog become a view of `STATUS.md`?** Recommend no.
  Leave it until the table has run for a few weeks.

## Sequencing

1. Build the status table in Perry first. It is small and pays off at once. It
   becomes the first content of the method repo.
2. Then extract `claude-method` from Perry and from `tmdc-web`. Use `tmdc-web`
   as the test that the template works on a repo that is not Perry.
3. Do not bundle the migration of the 40 status lines with the script. Land
   the script and check first, run the migration as a separate commit, and
   review the mapping before it commits.
4. Do not build the plugin (Part 2, way 1) before the status table works. The
   table decides what the skills must know.
5. `CHANGELOG.md` is unchanged. Nothing here is implemented, and the changelog
   records completions.
