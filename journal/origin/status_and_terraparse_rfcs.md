---
status: in-progress
status_changed: 2026-09-25
type: note
next: Run the four-week tests from 2026-10-21 (section 5, What this does not show). Keep or drop the format on that result.
---

# STATUS.md and TerraParse RFCs — one lightweight proposal format for one developer and many LLMs

**Status: IMPLEMENTED (committed 2026-09-24 as `dde1a78`).** Written 2026-09-23 from a chat with Claude. The owner
approved the proposal and every recommendation the same day, with one change:
Q3 (numbering) went the other way. Everything built and applied on 2026-09-23 (Sequencing steps 1 to 6, plus the three items first left
undone on purpose). It was committed on 2026-09-24. See "8. Implementation record", "9. Step 6 applied" and
"10. Follow-ups" at the end. "TerraParse RFCs" is a
working name. This note holds the full proposal. The chat-derived background
sits in `teaching_repos_my_claude_method.md`, which covers rolling the method
out to other repos and is not repeated here.

**Revised 2026-09-23, second pass, after owner review.** Two gaps were found in
the first draft. (1) It fixed the frontmatter and said the body was "unchanged",
but the existing plan docs carry explanatory sections (problem, design, scope)
that the draft did not account for. The new "The body" section in this note
adds allowed formats for them. (2) The check script only read frontmatter. It
now also checks the body. The first draft's line "BQRS stays exactly four
sections" was too literal. See "The body" and Q7.

**Revised again 2026-09-23.** The two frontmatter keys `kind` and `front` are
merged into one key, `type`. The two keys came from adding requirements one at
a time. No check rule needs them apart, and one key cannot hold a contradictory
pair such as `kind: note` with `front: design`.

The frontmatter block below is the format this note proposes. This note is its
first example, but it is `type: note`. It has no Blockers, Questions,
Recommendations and Sequencing sections in the BQRS shape, so it would fail the
plan check. The scripts read it (see the implementation record).

## 1. The problem

Ideas for features sit in different stages: an idea, a plan under review, code
in progress, code shipped. Two facts make this hard to track:

- **Status has no single home.** 40 of the 50 docs in
  `journal/v0-6/refactoring/` open with a free-text `**Status: ...**` line. The
  words differ from doc to doc. No file collects them. `journal/CHANGELOG.md`
  lists completions only, so an unshipped idea appears nowhere.
- **Every LLM session starts cold.** A session has no memory of the last one.
  The repo files are the only state that survives. A status held in the
  owner's head, or in a chat transcript, is lost.

## 2. The proposal

A **TerraParse RFC** (Request for Comments) is a design doc that has three
parts:

1. **A frontmatter block** with a fixed set of fields (see "3. The format").
2. **A body in two parts.** An explanatory front part (the problem, the design,
   the scope), then the BQRS decision part. BQRS means Blockers, Questions,
   Recommendations, Sequencing, the required plan shape in
   `docs/conventions.md`. BQRS itself is unchanged.
3. **A generated index**, `journal/STATUS.md`, built by a script from the
   frontmatter of every RFC. Nobody edits it by hand. A second script checks
   that the frontmatter and the body are valid.

Existing docs are not rewritten. Each one gets a `type: legacy` marker and
stays as written.

## 3. The format

### Frontmatter

```yaml
---
status: planning            # one of the five states below
status_changed: 2026-09-23  # date of the last status change
type: design                # design | legacy | note
next: One line. The next action, or what blocks it.
blocked_by: other_doc.md    # optional. A filename
superseded_by: new_doc.md   # optional. Only when status is closed/superseded
closed_reason: superseded   # only when status is closed. superseded | rejected | withdrawn | reference
---
```

`type` says which body format the doc follows, and so which body rules the
check applies (see "The body"). `design` is the one plan format (2026-09-25:
`pitch` and `decision` were removed, see section 13). `legacy` is a plan written before this format existed, and its
body is not checked. `note` is everything that is not a proposal: a research
note, a corrections list, a reference, an index. A `note` also gets no body
check. Every type gets the frontmatter check.

### States

| State | Meaning |
|---|---|
| `planning` | A `design` doc exists, from its first draft. The owner has not approved it. |
| `ready` | The owner approved it. Work has not started. |
| `in-progress` | Code is being written. |
| `implemented` | Merged and applied. |
| `closed` | Ended without shipping. `closed_reason` says why. |

A `note` uses two of these states only: `in-progress` (the note is still being worked on) and `closed` (it is done
or set aside; `closed_reason` says which). A note is never planned, approved or shipped. A `legacy` doc may use any
state.

"Blocked" is not a state. `blocked_by` and `next` carry it.

### Moves between states

| Move | Who and what triggers it |
|---|---|
| `planning` to `ready` | The owner approves. Zero `[open]` blockers remain (the check enforces this). |
| `ready` to `in-progress` | Work starts. |
| `in-progress` to `implemented` | Code is merged and applied. If the work created or deleted a file under `perry/`, `docs/architecture_map.md` is updated first (existing rule). |
| any state to `closed` | The owner decides. Set `closed_reason`. |
| `in-progress` back to `planning` | A new blocker appears. Add a dated note to the doc. |

`status_changed` overwrites. Git holds the history. The dated note follows
the existing rule: annotate, do not rewrite.

### Blocker tags

Each blocker item carries a tag on its first line. Existing docs write items in
three styles, and the check accepts all three:

```markdown
### B1 — The check parses tags, not prose [resolved]
**B2. Removing the `parsed.md` write must not remove the archive [open]**
**B3 — n=3. The direction is established; the magnitude is not. [open]**
```

The check script counts `[open]` tags. It fails when a doc has `status: ready`
or `in-progress` and one or more `[open]` blockers. It counts tags in the body,
and it does not read a duplicate count from frontmatter (see Q1).

### The body

**What the existing docs look like.** I surveyed the 50 docs in
`journal/v0-6/refactoring/` on 2026-09-23 by reading their headings. The counts
are approximate, because they come from a text search:

- A plan has three zones. Explanatory sections come first ("What this is, in
  one sentence", "The design", "What this does not fix"). The decision sections
  follow (Blockers, Questions, sometimes Recommendations and Sequencing). Dated
  notes come last ("What was built", "Implementation record", "execution
  note").
- Only two docs show all four BQRS headings (a script count, 2026-09-23):
  `resume_stage_shortcuts.md` and `s3_prefix_split.md`. The first draft of this
  note said "about four". That was a guess from a text search, and it was
  wrong. The name BQRS dates from 2026-09-10. Older docs stop at Blockers and
  Questions, or scatter blockers through the body (`pdf_table_extraction.md`,
  `reading_list_feature.md`).
- Blocker and question items use three styles (above). 41 of the 50 docs carry
  a bold `**Recommendation` line inside an item. 15 write a question's answer
  as `**Q1 — the question?** → **The answer.**` instead. The check accepts both.
- Some docs are not plans: `publisher_issue_research_note.md` (a research
  note), `run9_corrections.md` (a corrections list).

**A conflict, settled 2026-09-23.** `docs/conventions.md` said a BQRS doc "has
exactly these four sections, in this order." Read literally, that bars the
explanatory front, and no existing doc follows it that way. The owner approved
Q7, and the rule now reads: the decision part is exactly these four sections,
in this order, after the explanatory sections and before dated notes. The edit
is in `docs/conventions.md`.

**The shape of a plan body:**

```
frontmatter
# Title
Status line and one opening paragraph
## Front sections      (roles below; the order is free)
## Blockers
## Questions
## Recommendations
## Sequencing
## <YYYY-MM-DD> ...     (zero or more dated notes, added after the fact)
```

**Front sections have roles, not fixed titles.** The check does not demand
exact headings. It matches each front heading to a *role* through an alias
table, so the titles already in use keep working:

| Role | It answers | Headings already in use (aliases) | Comes from |
|---|---|---|---|
| `summary` | What is this? | "What this is, in one sentence", "What changed" | KEP Summary; Rust RFC Summary; PEP Abstract |
| `motivation` | Why, and what is wrong today? | "Why we were looking", "The problem, stated plainly", "Why, in the terms the project owner used" | KEP and Rust Motivation; Shape Up Problem; ADR and MADR Context |
| `scope` | What is in, and what is out? | "What this does not do", "What this does not fix", "What this leaves open", "Scope, in one table" | KEP Goals and Non-Goals; Google Goals and non-goals; Shape Up No-gos |
| `design` | What do we build? | "The design", "The shape", "The proposed shape", "Where it plugs into the code", "Implementation shape" | KEP Proposal and Design Details; Rust Guide- and Reference-level explanation; PEP Specification; Shape Up Solution |
| `alternatives` | What else did we weigh? | "Options", "Alternatives considered" | KEP and Rust Alternatives; MADR Considered Options; PEP Rejected Ideas |
| `evidence` | What did we measure? | "What is true today — measured", "What exists today", "Findings", "Pilot results" | This project's own practice; nearest outside form is Rust Prior art |
| `verification` | How do we know it works? | "Verification", "Tests", "Negative controls to execute, not reason about" | KEP Test Plan |
| `history` | What was built? (added after the fact) | "What was built (date)", "Implementation record (date)", a dated execution note | KEP Implementation History |

A front heading that matches no alias is allowed. The report lists it as
"unclassified" and does not fail on it. The alias table above is a starting
point. It is tuned against the real docs (see B1).

**One plan format.** (Until 2026-09-25 there were three, `pitch`, `design` and `decision`. See section 13.) `type:` picks the body format:

| `type` | Use when | Required roles | Lineage |
|---|---|---|---|
| `design` | A normal feature or refactor. The default. | `summary` or `motivation` (either one). `design` and `scope` are expected (warn) | KEP; Rust RFC |
| `legacy` | Every plan written before this format. Body not checked. | none | — |
| `note` | Not a proposal: research note, corrections list, reference, index. Body not checked. | none | — |

A required role is a section that matches an alias and has at least one
non-blank line under it. An *expected* role only warns when it is missing.
The required roles were relaxed on 2026-09-23 after the corpus trial: only 1
of 50 real refactoring docs has all four of summary, motivation, design and
scope as sections, and requiring them would push writers to add empty headings.
`evidence` and `verification` are optional in every format. `history` becomes
required when `status` is `implemented` (see the check rules).

A `design` doc then needs the four BQRS decision sections. A small idea is a short
`design` doc, and a section may be one line, or "None — because ...". A choice among
options goes in the Questions section, with the options and a recommendation. The
existing rule already says a review that finds no blockers must say so and say
why.

A dated note after Sequencing must carry a date in its heading. That keeps the
existing rule: annotate, do not rewrite history.

### The generated index

`journal/STATUS.md` has three blocks, in this order, plus a last block for
documents without frontmatter. Rows below are illustrative. Only the two
`implemented` dates come from `journal/CHANGELOG.md`.

**Active** (`ready` and `in-progress`, newest first). Empty if nothing is in
flight.

**Planning** (`planning`, newest first). The heading carries the count:
"Planning — awaiting the owner (N)". This is the owner's review queue: every
document that has a plan and no approval yet. Empty if nothing waits. (Added
2026-09-24 at the owner's request. It replaces a one-line "Awaiting the owner:
N" count that sat above Active, because the count and the list should come
from the same rows.)

**All** (every RFC, sorted by `status_changed`, newest first):

| Changed | Doc | Status | Next |
|---|---|---|---|
| 2026-09-23 | `status_and_terraparse_rfcs.md` | planning | Owner reviews |
| 2026-09-14 | `reading_list_feature.md` | implemented | — |
| 2026-09-11 | `shortlist_topup.md` | implemented | — |

The real file also has a `No.` column. The script scans every `.md` file under
`journal/` except `CHANGELOG.md` and `STATUS.md` (127 files on 2026-09-23), not
a list of directories. Documents without frontmatter appear in a last block, so
the index works during the migration.

### The check script

`scripts/check_status.sh` runs the frontmatter rules, the body rules and the
index check. It is a thin wrapper over `scripts/check_status.py`. All rules
live in `scripts/rfc_lib.py`, and `scripts/build_status.py` uses the same
parser. Each failure prints a code. The codes below are what the tests assert.

**Frontmatter rules.** These run on every document. The check fails when:

| Code | Fails when |
|---|---|
| `fm-missing` | The file has no frontmatter block. |
| `fm-yaml` | The block does not parse, or is not a `key: value` mapping. |
| `fm-type` | `type` is missing or is not one of the three values. |
| `fm-status` | `status` is not one of the five states. |
| `fm-status-type` | A `note` has a status other than `in-progress` or `closed`. |
| `fm-date` | `status_changed` is missing or is not a `YYYY-MM-DD` date. |
| `fm-closed-reason` | `status: closed` has no valid `closed_reason`. |
| `fm-link` | `blocked_by` or `superseded_by` names a file that is not under `journal/`. |
| `fm-id` | A `design` file has no `NNNN_` number prefix. |
| `fm-id-dup` | Two files use the same number. |
| `stale-index` | `journal/STATUS.md` is missing or differs from what the frontmatter generates. |

**Body rules.** These run only on the plan type (`design`):

| Code | Fails when |
|---|---|
| `body-roles` | A required role has no non-empty matching section before the decision sections. |
| `body-order` | A decision section is missing or repeated, the four are not in order Blockers, Questions, Recommendations, Sequencing, or a non-decision section sits between them. |
| `body-dated` | A section after Sequencing has no `YYYY-MM-DD` in its heading. |
| `body-empty` | Blockers or Questions has no items and does not say "None" with a reason. |
| `body-items` | An item ID repeats, or a `Q` item sits in Blockers (or the reverse). |
| `body-tag` | A blocker does not carry exactly one `[open]` or `[resolved]` tag on its first line. |
| `body-recommend` | A question, or an `[open]` blocker, has no recommendation: a `**Recommend` run-in, or `→ **answer**`. |
| `body-r-cover` | A question or an `[open]` blocker does not appear in Recommendations. |
| `gate-open-blocker` | `status` is `ready` or `in-progress` and an `[open]` blocker remains. |
| `body-history` | `status` is `implemented` and no section is in the `history` role. |

**Three rules differ from the first draft, because of the corpus trial** (see the
implementation record): a `[resolved]` blocker needs no recommendation and no
Recommendations entry; a question's recommendation may use the arrow form; and
the order of Recommendations against item order is a warning, not a failure.

**Warnings never fail a run.** More than three `in-progress` documents. A front
heading that matches no alias. An expected role that is missing. Recommendations
out of item order. A bare section reference (`§4` with no document; a hint only,
since `spec §4.2` and stage tokens like `S07` are legal).

**Negative controls.** `tests/test_rfc_check.py` starts from three passing
fixtures (`tests/rfc_fixtures/`, one per plan type; one today), changes one thing, and
requires exactly that rule's code. `tests/test_propose_frontmatter.py` covers the
migration script. A rule whose test does not fail when the rule is removed has
proved nothing, so each rule was disabled in turn and its test was seen to fail
(see the implementation record).

**What the script cannot check.** It checks that the structure is present. It
cannot check that the content is good. A model can write `**Recommendation:
yes.**` and pass `body-recommend` and `body-r-cover`. It cannot tell whether an
item filed as a Question is really a Blocker. It cannot tell whether a
recommendation rests on this project's history, as `docs/conventions.md`
requires. That work stays with a review step: the owner, or a
`review-planning-doc` skill (see `teaching_repos_my_claude_method.md`) that
reads the doc against those standards. Do not read a passing check as a passing
review.

## 4. Influences, and what each one gave

| Influence | What was borrowed | What was not borrowed |
|---|---|---|
| **Python PEP 0** (Python Enhancement Proposal) | The index is generated from each document's header. Nobody edits it. A `Superseded-By` header links old to new. | Public review, numbered documents, the nine-state lifecycle. |
| **Kubernetes KEP** (Kubernetes Enhancement Proposal) | A small metadata block (`kep.yaml`) beside the proposal. The status words `provisional`, `implementable`, `implemented`, `deferred`, `rejected`, `withdrawn`, `replaced` (verified 2026-09-23 against the template's `kep.yaml`). Progress kept in a separate field from status. The section vocabulary for `summary`, `motivation`, `scope`, `design`, `alternatives`, `verification` (Test Plan) and `history` (Implementation History), read from the template's README on 2026-09-23. | The remaining sections (Release Signoff Checklist, Graduation Criteria, Version Skew Strategy, the whole Production Readiness Review group), the release-cycle process, and the seven-value status list itself. Six states are enough here. |
| **Rust RFC** | A required "Unresolved questions" section. A proposal is short and text-only. The shape Summary, Motivation, Explanation, Rationale and alternatives. | The public comment period, the team sign-off, Prior art and Future possibilities as required sections. |
| **Architecture Decision Record (ADR)** | A record is not rewritten. When a decision changes, a new record supersedes the old one, and the old one stays. The Context, Options, Decision shape, now used inside a Questions item of a `design` doc. | One decision per file as a rule. A BQRS doc may hold many. |
| **Kanban** | Few flow states. A cap on work in progress. "Blocked" is a flag on a card, not a column. | Boards, swim lanes, pull signals. |
| **Shape Up** (Basecamp) | A proposal is shaped before anyone commits to build it. The Problem, Solution, No-gos shape, for a short `design` doc. "Rabbit holes" as a name for the risks found in shaping. | Fixed six-week cycles, the betting table, appetite. |
| **Google-style design doc** | Context and scope, Goals and non-goals, The design, Alternatives considered. This confirms the `scope` role and its aliases. | Cross-cutting concerns as a required section. |
| **This project's own rules** | BQRS itself. A blocker is where a wrong answer gives a quietly incorrect system. Every item carries a recommendation. Dated notes instead of rewrites. A check script beats a written rule (`scripts/check_claude_md.sh`). The front-section headings already in use become the alias table. | — |

I have not checked the PEP, Rust RFC, ADR, MADR, Kanban, Shape Up or Google
items against their current docs. They are from Claude's memory, which stops at
January 2026. Only the KEP row is verified, and the fetch that verified it went
through a summarizing tool. Re-read the raw KEP template before copying its
wording.

**What the common core is.** All of these sources agree on the same five
questions: what is this and why (summary, motivation), what do we build
(design), what is out of scope (non-goals), what else did we weigh
(alternatives), and what happened (history). The role table above is those five
questions, plus this project's two additions, `evidence` and `verification`. The
sources differ on how much ceremony surrounds them. The formats differ only in
which of the five a doc must answer.

## 5. Why this fits one developer and many LLMs

Public RFC processes solve a coordination problem: many humans must agree, and
their work must not collide. This project has one human. That cost is zero, so
the proposal drops the consensus machinery. It keeps the parts that solve two
other problems: lost memory and drifting records.

1. **`STATUS.md` is the cold-start file.** A new session reads one file and
   knows what is planned, in flight and done. No session depends on the last
   one's memory. A single line in root `CLAUDE.md` can name the file. That line
   is a standing rule, not a dated change note.
2. **The doc is the source of truth, so sessions cannot disagree.** Two LLM
   sessions, or two different LLM tools, read the same frontmatter. The index
   is generated, so it cannot hold a value that differs from its source. This
   avoids the failure this project has shipped a dozen times: a value written
   with no reader.
3. **A script enforces the rules. A model's compliance does not.** An LLM can
   forget a convention between sessions. A check that fails on a missing status
   does not forget. This is the lesson of `check_claude_md.sh`.
4. **The body needs the check as much as the frontmatter.** An LLM can write
   valid frontmatter over a hollow body: a `ready` doc with no scope section, or
   a blocker with no recommendation. The frontmatter says the doc is ready. Only
   a body check tests that claim.
5. **Fixed roles make a doc fast to read cold.** A session that opens a plan
   knows the decisions are in Blockers and Questions, and the reasons are in
   the front sections, without reading the whole doc. The formats pick the
   ceremony by size, so a small idea does not pay for a large template.
6. **Closed docs record why not.** A `closed` doc with `closed_reason:
   rejected` tells a future session that the idea was tried on paper and why it
   failed. Without it, a session proposes the same idea again.
7. **Plain markdown and YAML work with any tool.** Nothing depends on a Claude
   Code feature. A different agent, or none, can read the files. The repo
   already has notes on moving to OpenHands.
8. **The human stays the approver.** An LLM drafts the BQRS doc. The owner
   reads it as a review of a proposal. `planning` to `ready` is the owner's
   move, and the blocker gate backs it with a mechanical check. This matches
   the review discipline already in `docs/conventions.md`.
9. **The scarce resource is the owner's attention.** Many LLM sessions can
   write faster than one person can review. The Planning block therefore lists
   every item awaiting the owner, so the review queue is one section and not a
   search. The cap is a warning, and not a hard stop,
   because this project's own rule is that ordering beats capping for reviewer
   attention. The table's newest-first order carries the load.
10. **A stub costs almost nothing.** An idea gets a five-line file. An LLM
    expands it later, when the owner picks it. (2026-09-25: the `idea` state was
    removed, so a stub starts as a short `design` doc in `planning`. See section 14.)

### What this does not show

The argument above is reasoning. Nothing was measured. The project's own rule
is to set the bar before seeing the data, so these are the tests, fixed now:

- After four weeks, a fresh session finds the state of every RFC from
  `STATUS.md` alone. Check it by asking one.
- The check script has failed at least once on a real error, and at least once
  its negative control has failed correctly (see Sequencing).
- Zero RFCs have a `status` that disagrees with the code's real state. Sample
  five.
- Two real docs, `resume_stage_shortcuts.md` and `s3_prefix_split.md`, pass the
  body check as `type: design` after only three changes: add frontmatter, add
  blocker tags, add item IDs where missing. If they need more, the alias table
  or the rules are too strict. Fix the format, not the docs. **Result
  2026-09-23: not met as written.** See the implementation record.

If two of the first three fail, drop the format and keep only the generated
index. (2026-09-25: `pitch` and `decision` were deleted early. See section 13.)

## 6. Open decisions, with recommendations

**Blockers: one.** A wrong answer to any question below gives a slower or
clumsier workflow, and none gives a quietly wrong system. The exception is the
check itself.

- **B1. The alias table can be too loose or too strict, and a loose one passes
  hollow docs without any sign.** A heading such as "Design" matching a section
  that holds two lines would count as a `design` role. Recommend three
  measures, all before the check is trusted. First, keep the non-blank-line
  rule (rule 7). Second, run the check over all 50 existing docs and read the
  "unclassified" list, so the alias table comes from the real headings and not
  from this note. Third, ship the negative-control fixtures and run each one to
  a failure. The bar for "not too strict" is the two-doc test in "What this does
  not show". Set before seeing the data.

Questions (any answer gives a working system):

- **Q1. Tags on blocker items, or a count in frontmatter?** Recommend tags.
  A count duplicates a fact the body already states, and the two can drift.
- **Q2. Who may set `ready`?** Recommend a convention: only the owner. The
  check cannot tell who edited a file, so this is a rule in root `CLAUDE.md`,
  not a mechanical gate. Revisit if an LLM breaks it once.
- **Q3. Number the RFCs, as PEP and KEP do?** **Decided by the owner
  2026-09-23: yes.** Claude had recommended no, on the grounds that filenames
  already work; the owner overrode that. The scheme, as built: the number is the
  filename prefix, `NNNN_slug.md` (for example `0049_status_index.md`), and lives
  nowhere else, so it cannot disagree with a copy of itself. New RFCs start at
  49. Numbers 1 to 48 are reserved for renumbering the legacy documents later.
  `scripts/build_status.py --next-id` prints the next free number, and never
  lowers if a low number is used. A `design` file must
  have a number (`fm-id`). Two files may not share one (`fm-id-dup`). A `legacy`
  or `note` file may carry one, and no existing file has one yet. A citation by
  filename already includes the number, so the citation rule needs no change.
  Renaming a legacy file when it is numbered will break prose that cites its old
  name, and that is the owner's planned event to handle.
- **Q4. Record each decided blocker as an ADR?** Recommend no for now. It
  doubles the file count, and the resolved blocker already sits in its doc.
- **Q5. Where does the script live before the method repo exists?** Recommend
  `scripts/build_status.py` and `scripts/check_status.sh` in Perry, next to
  `check_claude_md.sh`.
- **Q6. Should this note's frontmatter become the format for all new notes?**
  Recommend yes, from the day the check script lands. Old docs migrate in a
  separate commit.
- **Q7. Amend `docs/conventions.md` so the BQRS rule reads "exactly four
  decision sections, in this order, after the explanatory sections"?**
  Recommend yes, and the owner should make the edit, since the rule is a stated
  standing preference. Without it, the conventions file and the check disagree,
  and a cold session that reads only the conventions could strip the front
  sections from a plan. Do it in the same change that lands the check.
- **Q8. Retrofit old docs to `design`, or mark them `legacy`?** Recommend
  `legacy`. About 40 docs predate BQRS and would need new sections, IDs and tags.
  That rewrites history and adds no information. Upgrade a doc to a real
  format only when work reopens it, and record the upgrade as a dated note.
- **Q9. Keep three front formats, or one?** Recommend three for now, with the
  deletion bar above. A single format forces a one-line idea through a
  four-role template, which is the cost that makes an idea not get written.
- **Q10. Should `history` be a required role for `implemented`?** Recommend
  yes (`body-history`). It catches a doc marked `implemented` with no record of what
  was built. `pdf_table_extraction.md` shows the pattern to keep ("What was
  built", dated).
- **Q11 (new). Decided 2026-09-23: agreed, no.** `resume_stage_shortcuts.md` fails `body-history` when converted
  with its real status. Should a dated trailing section count as `history`?
  Recommend no. The rule exists to catch an implemented doc that records nothing
  about what was built, and this doc records it in a paragraph with no
  identifying title. Leave the doc `legacy`.
- **Q12 (new). Decided 2026-09-23: agreed, keep.** The proposal marked 71 documents (specs, guides, diagrams, notes
  with no status line) `closed` with reason `reference`. That reads oddly for a
  live spec. Recommend keeping it for now: `closed` here means "not a proposal
  in flight", and a seventh state would only be used for these. Revisit if the
  index reads badly.
- **Q13 (new). Decided 2026-09-23: agreed; the sentence in `docs/conventions.md` is amended.** It said Recommendations restate items "in
  the same order". Both exemplar docs sort by priority instead. The check now
  only warns. Recommend amending the sentence to "in priority order, naming each
  item's ID", in the same edit as Q7's follow-up.

## 7. Sequencing

**Progress 2026-09-23:** steps 1 to 6 are done, and step 9 (the changelog line) is done. Step 8, the
four-week tests, starts after 2026-10-21. Step 7, the plugin work, is separate.

1. **Decide Q7 first.** The order and names of the decision sections are what
   the check enforces. Settle the rule before writing code that encodes it.
2. **Write the check script next, with negative controls.** A test that agrees
   with the bug proves nothing. Ship the fixtures for rules 1 to 14 and run each
   one to a failure. Add one passing fixture per format.
3. **Run the check over the 50 existing docs before trusting it** (B1). Read
   the "unclassified" list. Adjust the alias table from what it shows.
4. **Convert two real docs** (`resume_stage_shortcuts.md`,
   `s3_prefix_split.md`) as the two-doc test. Do this before migrating anything
   else.
5. **Then the generator.** It reads the same frontmatter parser as the check.
6. **Then migrate the 40 existing status lines.** A separate commit. A script
   proposes the status mapping, sets `type: legacy`, and flags ambiguous docs.
   The owner reviews it before it lands.
7. **Do not bundle** the plugin or template work from
   `teaching_repos_my_claude_method.md` with this. That work needs a proven
   format to copy. The `review-planning-doc` skill, which covers the meaning
   the script cannot check, belongs to that later work.
8. **After four weeks, run the tests in "What this does not show".** Keep or
   drop the format on that result.
9. **`journal/CHANGELOG.md` is unchanged** until something here ships.

## 8. Implementation record

**2026-09-23, steps 1 to 5 of Sequencing.** Step 6 is prepared and not applied.

### What was built

| File | What it is |
|---|---|
| `scripts/rfc_lib.py` | The one parser and all rules. Reads files; never writes one. |
| `scripts/check_status.py`, `check_status.sh` | The check. `--survey [DIR]` prints a read-only heading survey. |
| `scripts/build_status.py` | Writes `journal/STATUS.md`. `--next-id` prints the next free number. |
| `scripts/propose_frontmatter.py` | Step 6: writes a proposal table, and `--apply` reads the reviewed table back. |
| `tests/test_rfc_check.py`, `tests/test_propose_frontmatter.py`, `tests/rfc_fixtures/` | 66 tests and three passing fixtures. |
| `journal/STATUS.md` | Generated. At this point it lists two documents with frontmatter and the rest under "No frontmatter yet". |
| `journal/misc/status_migration_proposal.md` | Generated. 126 rows. Nothing applied. |
| `docs/conventions.md` | The BQRS sentence amended (Q7). No dated heading was added. |

No file under `perry/` changed, so `docs/architecture_map.md` needed no row.

### Step 1, Q7

Done, as approved. `docs/conventions.md` now says the decision part is exactly
the four sections, after the explanatory sections and before dated notes.

### Step 2, negative controls

Each rule has a test that starts from a passing fixture, changes one thing, and
requires exactly that rule's code (51 tests). To prove the tests can fail, each of
the 20 rule codes in `rfc_lib.py`, and `stale-index` in `check_status.py`, was
disabled in turn by editing its `Finding(...)` code, and at least one test went
red every time. The file was restored from a backup and checked with `cmp` after each
loop. The loop ran twice: once before, and once after, the format changes below.
`body-r-order` was retired in between (it became a warning).

### Step 3, the corpus trial

The survey read all 127 documents under `journal/`. For the 50 in
`journal/v0-6/refactoring/`, the headings show: Blockers in 32, Questions in 38,
Recommendations in 6, Sequencing in 15, and all four in 2. Then each of the 50
was treated in memory as `type: design`, with no file changed:

- **Before any change:** 0 of 50 passed. Failures: `body-roles` 49,
  `body-order` 48, `body-tag` 31, `body-recommend` 28, `body-r-cover` 6.
- **After the four format changes below:** still 0 of 50 pass, and that is
  expected: none of them has blocker tags yet, and 48 lack a Recommendations or
  Sequencing section (`body-order`). `body-roles` fell from 49 to 32, and
  `body-recommend` from 28 to 15.

### Step 4, the two-doc test

**The bar, set before the data, was not met as written.** Copies of the two docs
were converted in a scratch repo with only the allowed changes:

- `s3_prefix_split.md` **passes** after frontmatter, the number prefix, and
  blocker tags.
- `resume_stage_shortcuts.md` **passes every rule except `body-history`.** Its real
  status is implemented, and no section records what was built. Its record is a
  dated paragraph with no identifying title. See Q11.
- Both also needed the filename number prefix, a fourth change that the numbering
  decision (Q3) added after the bar was written.

Before any format change, the two docs failed on `body-roles`, `body-tag`,
`body-recommend`, `body-r-cover` and `body-r-order`.

### Format changes made because of steps 3 and 4

The note said: if the docs need more than three changes, fix the format. Four
changes were made. Each rests on a fact from the real docs, not on making the
count pass:

1. **The arrow form is a recommendation.** 15 docs write `**Q1 — ...?** → **Answer.**`.
   The `**Recommend` marker rejected them.
2. **A `[resolved]` blocker needs no recommendation and no Recommendations entry.**
   `resume_stage_shortcuts.md` B3 and `s3_prefix_split.md` B1 are blockers that were
   checked and cleared ("No blocker"). Only `[open]` blockers and all questions
   need one.
3. **Recommendations order is a warning.** Both exemplar lists sort by priority,
   not by item number.
4. **Required front roles were relaxed.** Only 1 of 50 docs has all four of summary,
   motivation, design and scope as sections. `design` now requires a summary or
   a motivation. `design` and `scope` warn when missing. `pitch` requires
   motivation and design.

**Not changed:** `body-history` (Q11). It found a real gap, so it stays.

### Step 5, the generator

`journal/STATUS.md` was generated. It is deterministic (no timestamp), and
`check_status` fails with `stale-index` when it differs from what the frontmatter
generates.

### Step 6, prepared and not applied

`journal/misc/status_migration_proposal.md` holds one row per document without
frontmatter: 126 rows, 79 carrying a flag. Most flags are "no status line".

| Proposed type / status | Rows |
|---|---|
| `note` / `closed` / `reference` | 71 |
| `legacy` / `implemented` | 24 |
| `legacy` / `closed` / `reference` | 11 |
| `legacy` / `planning` | 10 |
| `note` / `planning` | 6 |
| `note` / `implemented` | 3 |
| `legacy` / `closed` / `superseded` | 1 |

**A dry run was done on a scratch copy of `journal/`:** apply the table,
regenerate `STATUS.md`, run the check. Result: 126 documents changed, then
`OK: 128 document(s) pass`, exit 0. The real `journal/` was not touched.

Owner steps to finish it:

1. Read the table, above all the rows flagged `ambiguous` or `unrecognised`, and
   the rows where `basis` says `status: none`. The `s3_prefix_split.md` row, for
   example, says `closed` / `reference`, but the doc is implemented.
2. `venv/bin/python scripts/propose_frontmatter.py --apply`
3. `venv/bin/python scripts/build_status.py`
4. `scripts/check_status.sh` (should print OK)

### Left undone on purpose

- **The standing-rule section in `docs/conventions.md` and the one line in root
  `CLAUDE.md`** ("read `journal/STATUS.md` first when picking up work"). Adding
  them now would tell every session to run a check that fails on 126 documents
  until step 6 lands. Add both in the step 6 change.
- **The `journal/CHANGELOG.md` line.** Add it when the migration lands.
- **The plugin and copier work** (`teaching_repos_my_claude_method.md`), by design.
- **Nothing was committed.** The working tree holds all changes.

## 9. Step 6 applied

**2026-09-23.** The owner agreed Q11 (no), Q12 (keep) and Q13 (amend) and asked for the migration.
Before applying, the flagged rows were reviewed. That review found that the first classifier was
wrong in enough places to matter, so it was fixed and the table was regenerated.

### What the review found in the first proposal

Of the 79 flagged rows, checked against `journal/CHANGELOG.md` and the doc bodies:

- **A leading verdict must win.** `batch_extraction.md`, `coverage_audit_removal.md` and
  `search_redesign.md` start with `IMPLEMENTED` but mention "the planning document" later. The
  first classifier called them `planning`. `cheap_extraction_tier.md` said `IMPLEMENTED ... B1 and B3
  closed` and came out `closed`.
- **A later negation means planning, and a later built-word means implemented.** "proposed
  2026-08-07, implemented and applied 2026-08-09" is implemented. The date is now the first one
  after the verdict word, not the first in the line.
- **Two status-line shapes were missed.** `**Status (2026-09-21): SUPERSEDED ...**` (a date in
  parentheses before the colon) made `semantic_claim_extraction_redesign.md` read as `planning`,
  from a struck-through old line. `**Date:** ... **Status:** proposal` (mid-line) made two proposal docs read as
  "no status line".
- **`CHANGELOG.md` is evidence.** A doc with no usable status line that the changelog links records
  a finished change, so it is now proposed `implemented`, dated by the changelog line. This fixed
  `s3_prefix_split.md` and `semantic_ranking_upgrades_v2.md`, among others.

All of this is in `scripts/propose_frontmatter.py` with tests. The proposal went from 79 flagged rows
to 59.

### Five rows corrected by hand

The proposal marks them `reviewed by hand`. Each has a reason:

| Doc | Now | Why |
|---|---|---|
| `misc/open_hands_transition_suggestions.md` | `planning`, 2026-09-16 | Its header line reads "Planning only". |
| `v0-4/perry_v0-4_spec.md` | `closed` / `reference` | The baseline spec `CLAUDE.md` treats as authoritative. "Draft for implementation" is stale. |
| `misc/claudemd_redesign.md` | `implemented`, 2026-09-14 | Its status line says nothing is implemented, but the split is done. Root `CLAUDE.md` is thin and `check_claude_md.sh` exists. |
| `v0-5/log_fix.md` | `implemented` | "analysis **and** implementation, both 2026-08-05". |
| `v0-6/per_spec_scope_dimensions.md` | `closed` / `superseded` | **My judgment; owner to confirm.** It proposes per-spec scope-dimension work. The four dimensions were then removed (`scope_field_removal.md`), so the proposal is moot. |

### Applied

- `propose_frontmatter.py --apply` prepended frontmatter to 126 documents. Before that, the
  script validates every cell against `rfc_lib.py` and refuses a doc that already has frontmatter.
- **Only additions:** 122 tracked files changed, +795 lines, 0 deleted. Four more docs were
  untracked and also got frontmatter: `teaching_repos_my_claude_method.md` and three
  `perry-web` handoff docs from the initial `git status`.
- `journal/STATUS.md` was regenerated: 128 documents. `scripts/check_status.sh` prints
  `OK: 128 document(s) pass (0 warning(s))`, exit 0. 73 tests pass.
- **By status:** 66 `closed`, 48 `implemented`, 13 `planning`, 1 `in-progress`. **By type:** 81 `note`,
  47 `legacy`. No `pitch`, `design` or `decision` doc exists yet, so no body rule has run on a real doc.
- The amended Q13 sentence is in `docs/conventions.md`. `check_claude_md.sh` still passes.

### Rows the owner should still look at

- **13 docs are `planning`. Some may be stale.** `run4_corrections.md` and `run9_corrections.md` both
  say "PLANNING", and both contain sections that record work done (a domain exclusion list;
  "Both log defects fixed"). `rescore_spec_provenance.md`, `document_storage_economics_v0-6.md`,
  `run_review_standardization.md`, `repeated_figures_fix.md` and `rerun_discovery_problem.md` have no evidence either way.
  Each counts toward "Awaiting the owner" in `STATUS.md` until fixed.
- **Fix notes with no status line are `closed` / `reference`.** Several `v0-5/*_fix.md` notes
  probably describe work that was done, so `implemented` would be more accurate. Only the ones
  the changelog links were promoted. That is Q12's cost.
- **`STATUS.md`'s Active block** holds only this note.

## 10. Follow-ups

**2026-09-23.** The owner confirmed the hand correction for `per_spec_scope_dimensions.md` and closed two
stale notes. Then the three items left undone on purpose were done.

### Closed and confirmed

- `journal/v0-6/per_spec_scope_dimensions.md`: `closed` / `superseded` confirmed. It now carries
  `superseded_by: scope_field_removal.md`, and the check verifies that the file exists.
- `journal/v0-6/refactoring/run4_corrections.md` and `run9_corrections.md`: both were stale at
  `planning`. Both are now `closed` with reason `reference`, not `withdrawn`, because each holds
  records of work that was done and `reference` means "kept as a record". Each got a dated note at the end.
  "Awaiting the owner" in `STATUS.md` drops from 13 to 10 (after the two closures and the proposal doc,
  which had been left at `planning`).

### The three items, done

1. **The standing-rule section** is in `docs/conventions.md`, titled "TerraParse RFCs and STATUS.md
   (standing preference)". It has no dated heading. It holds eight rules. One deviation from this
   note's Q2 recommendation: the "Claude never sets `ready`" rule sits in `docs/conventions.md`, not in root
   `CLAUDE.md`, because `docs/conventions.md` is imported by root `CLAUDE.md` and is where standing rules live.
2. **One bullet in root `CLAUDE.md`** points to `journal/STATUS.md`: read it first when picking work back up.
3. **One line in `journal/CHANGELOG.md`**, newest first, linking to this note.

### Still open

- **Nothing is committed.** `status` on this note stays `in-progress` until the working tree is committed.
  Then set it to `implemented`. That follows this note's own rule: `implemented` means merged and applied.
- **The four-week tests** (section 5, "What this does not show") can start from 2026-10-21.
- **The plugin and copier work** in `teaching_repos_my_claude_method.md` is still separate and not started.
- **Optional, not built:** a `PreToolUse` hook that runs `check_status.sh` on journal edits, like
  `check_claude_md_hook.sh`. The convention relies on the rule and on running the check before finishing.

## 11. The Planning block

**2026-09-24.** The owner asked for `STATUS.md` to have its own section for documents in `planning`.
The design change is in "The generated index" section above. What was built:

- `render_status` in `scripts/rfc_lib.py` now writes a block between Active and All:
  "Planning — awaiting the owner (N)". It lists every `planning` document, newest first, with the same
  columns as the other blocks. An empty block reads "Nothing is in planning."
- It replaces the one-line "Awaiting the owner: N in `planning`" count that sat above Active. The count is
  now in the heading, so the count and the list come from the same rows.
- `idea` stubs are not in this block. They show only in the full list. If the owner wants them
  visible too, that is a one-line change, and the heading would need a new name.
- Three tests were added and one was corrected (its Active block now ends at the Planning heading).
  To prove the new tests can fail, the planning list was emptied in the generator, and one test went red.
  The file was restored and checked with `cmp`. 76 tests pass.
- `journal/STATUS.md` was regenerated. Before the regeneration, `check_status.sh` failed with
  `stale-index`, as designed. After it, the check prints `OK: 128 document(s) pass`.

The block holds 10 documents on 2026-09-24. Two are not plans in flight and could be closed or
promoted: `publisher_issue_research_note.md` is a research note that the migration typed `legacy`, and
`teaching_repos_my_claude_method.md` is a `note`. The rest have no evidence either way about whether they are
stale (see "9. Step 6 applied").

### Outcome, 2026-09-24

The owner agreed to both recommendations. `publisher_issue_research_note.md` is now `closed` with reason
`reference`, and got a dated note at its end. `teaching_repos_my_claude_method.md` stays in `planning`, and now has
a `next` line saying that Part 2 is not started and waits for this format to be committed and run for four
weeks. The Planning block holds 9 documents.

### Committed, 2026-09-24

The owner committed the working tree as `dde1a78`. Status moved from `in-progress` to `implemented`,
which is the rule in "Moves between states": merged and applied. `next` now holds only the four-week tests.
The optional `PreToolUse` hook and the plugin and copier work are still not built.

## 12. The enforcement hooks

**2026-09-24.** The owner asked for the two hooks that "Still open" in section 10 called optional: a Claude Code
`Stop` hook and a git pre-commit hook. Both run `scripts/check_status.sh`. Section 10's "Optional, not built" line
is now out of date. Its plugin and copier item is still true.

### What was built

| File | What it does |
|---|---|
| `scripts/check_status_stop_hook.sh` | Runs when Claude ends a turn. If `journal/` has uncommitted changes and the check fails, it returns `{"decision": "block", "reason": ...}` with the last 30 lines of the check. Registered in `.claude/settings.json`, next to the existing `check_claude_md_hook.sh`. |
| `scripts/git-hooks/pre-commit` | Runs at `git commit` when the commit touches `journal/` or the check's own scripts. |
| `scripts/install_git_hooks.sh` | Sets `core.hooksPath` to `scripts/git-hooks/`. Run once per clone, because git does not carry the setting. |
| `tests/test_status_hooks.py` | 11 tests. Each builds a throwaway git repo and drives the real hook scripts. |

Also changed: the "TerraParse RFCs and STATUS.md" section in `docs/conventions.md` (the "run the check" bullet now
names both hooks), `docs/environment.md` (the once-per-clone install step), and `journal/CHANGELOG.md`.

### Design choices

- **The pre-commit hook checks the staged snapshot, not the working tree.** It exports the index with
  `git checkout-index` to a temp directory and runs the check there with `--root`. A bad file that is staged cannot pass
  because a fixed copy sits unstaged in the working tree. One test covers exactly this.
- **The Stop hook runs only when `journal/` has uncommitted changes.** A session that touched no journal doc is not
  blocked by a failure it did not cause.
- **The Stop hook lets the turn end when `stop_hook_active` is true.** A failure the model cannot fix cannot trap the
  session in a loop. It also reads stdin, so it is synchronous, as this environment's hook notes require.
- **The pre-commit hook skips commits that touch nothing it guards.** An older bad commit does not block an unrelated one.
- **`git commit --no-verify` bypasses the pre-commit hook.** That is git's standard escape. The Stop hook has no bypass.
  The convention says to use the flag only if the owner asks.

### Negative controls

Each hook behavior was disabled in turn, and at least one test went red every time: pre-commit never blocks (3
tests red); pre-commit checks the working tree (1); pre-commit drops the guard (1); Stop hook ignores
`stop_hook_active` (1); Stop hook drops the journal guard (1); Stop hook never blocks (1). Two tests were too weak on the
first pass. The guard tests passed even without the guard, because the tree they used had no bad committed doc. Both
now commit a bad doc first with `--no-verify`. Each file was restored from a backup and checked with `cmp`.

### Checked on the real repo

- Staging only `journal/STATUS.md` while its source note was unstaged: the hook refused, with `stale-index`.
  Staging the note as well: the hook passed. Everything was then unstaged, and the working tree was untouched.
- The Stop hook on the real tree (`journal/` dirty, check passing): silent, exit 0.
- `.claude/settings.json` parses with `jq -e`.

### Not verified

- **The Stop hook inside a live Claude Code session.** The tests drive the script with the documented JSON. Whether this
  environment reads `{"decision": "block"}` from a Stop hook, and whether it picks up the new entry without a restart
  (`/hooks` once, or restart, per the owner's notes), has not been seen. Check once by breaking a doc's `status` in a
  session and ending the turn.
- **The hook's use of `jq`.** It is installed here (jq 1.6). A clone without `jq` fails the Stop hook.

## 13. One plan type: `pitch` and `decision` removed

**2026-09-25.** The owner removed the `pitch` and `decision` types for the first terrastep implementation. The valid
types are now `design`, `legacy` and `note`. This section records the change. Sections 8 to 10 above are history and
still name `pitch` and `decision` as they did when written.

### Why

- **A pitch is a short `design` doc.** The two differ in length, not in kind. The only rule that separated them was that
  a pitch required `motivation` and `design` and a `design` doc required `summary` or `motivation`.
- **A decision is a section of a `design` doc.** The options and the chosen option belong in a Questions item, with a
  recommendation. A separate file for one choice splits the reasoning from the proposal it serves.
- **The bar in section 5 pointed the same way.** No real `pitch` or `decision` doc existed, so neither type had a use.

### What changed

| Place | Change |
|---|---|
| `seed/scripts/rfc_lib.py` | `PLAN_TYPES` is `("design",)`. `REQUIRED_ROLES` and `EXPECTED_ROLES` keep only `design`. The `alternatives` heading alias stays, so an "Options" section is still a classified front section. |
| `seed/tests/` | The pitch and decision fixtures and their two mutation cases are gone. The `blocked_by` test uses an inline `note` doc as its target. 83 tests pass. |
| `examples/perry/conventions_method_excerpt.md` | The numbering rule says to use `type: design`. It says where a choice goes. |

`type: pitch` or `type: decision` now fails `fm-type`. The BQRS rules are unchanged. They never depended on the removed types.

## 14. The `idea` state removed, and notes limited to two states

**2026-09-25.** The owner made two changes to the `status` key. Sections 3 to 12 above name `idea` and the six states as
they did when written.

1. **`idea` is gone.** A `design` doc starts in `planning`. A small idea is a short `design` doc (section 13), so
   there is no stub stage before a plan. The states are `planning`, `ready`, `in-progress`, `implemented`, `closed`.
2. **A `note` is `in-progress` or `closed`.** A note is not a proposal. It has no approval and nothing to ship, so
   `planning`, `ready` and `implemented` do not apply to it. `legacy` docs may use any of the five states.

### What changed

| Place | Change |
|---|---|
| `seed/scripts/rfc_lib.py` | `STATES` has five values. New `NOTE_STATES`. New failure `fm-status-type`: a `note` with another status. |
| `seed/scripts/propose_frontmatter.py` | A note proposed as `implemented` becomes `closed` / `reference`. A note proposed as `planning` becomes `in-progress`. `--apply` rejects a note with any other status. The proposal file's own frontmatter is `in-progress`. |
| `seed/tests/` | `idea` is not a state (a mutation test). A note in each of the five states (two pass, three fail). A `legacy` doc keeps its full range. Fixtures that used `idea` now use `in-progress` or `closed`. 91 tests pass. |
| `examples/perry/conventions_method_excerpt.md`, `handoff.md` | The state list has five values. |
| This note and `teaching_repos_my_claude_method.md` | Both are `type: note`, so both changed status. This note was `implemented` and is now `in-progress`, because its next action (the four-week tests) is still open. The teaching note was `planning` and is now `in-progress`. |

### Not decided

- **The Perry corpus.** Perry has 81 `note` docs, and most are `implemented`. Under the new rule they fail `fm-status-type` until
  each becomes `closed` (with a `closed_reason`) or `in-progress`. The proposal script now makes that mapping. Nobody has run it against Perry.
- **The `in-progress` cap of 3.** Notes now count toward it. Two notes here are `in-progress` already.
