---
status: implemented
status_changed: 2026-09-11
type: legacy
---

# Stage resume shortcuts — an accumulator that isn't idempotent, and claims stranded across process boundaries

**Status: BUILT, 2026-09-11.** Approved by the owner, then implemented the
same day — all four remaining recommendations (the S04/S06 skip, the
S09/S10/S12 reconciliation, and the two repairs already recorded below)
landed together, matching §5's own allowance that the two mechanism fixes
"can land in either order or together." See CLAUDE.md's *"A resume no longer
re-derives everything from scratch in one process"* (2026-09-11) for the
test counts and what shipped; this document is kept as the design record,
not rewritten to read as if it always described finished work (GR-2).

- **Recommendation 6 (rescore) — DONE, 2026-09-11.** `perry rescore --variable
  Fuel_Cost_Stage_1 --project nbc` (owner-run). Verified after: 47 claims
  `REVIEW_READY` (promoted from `VALIDATED`), 27 `NEEDS_FOLLOW_UP`, 15
  `QUARANTINED`; all 74 rescorable claims carry a `claim_quality` row,
  `quality_score_version='v5'`, mean 18.22/27.
- **Recommendation 1 / B2 (the `relevance_score` repair) — DONE, 2026-09-11.**
  Re-verified live immediately before repairing (still 2.0x on all 882 rows —
  confirming the corruption had not self-corrected or been touched since it
  was found), then repaired by overwriting `variable_document_state.
  relevance_score` with a fresh one-pass recomputation from
  `search_results_for_run(10)` (B2's own prescribed method — not a `/2`
  divide). Verified after: all 882 rows read exactly `1.0` against the same
  independent recomputation used to detect the corruption in the first place
  (`min 0.9999999999999968, median 0.9999999999999997, max 1.0000000000000042`
  — floating-point noise around exactly 1, not a partial fix).
- **Recommendation 2 / B1 (the false "idempotent" comment) — DONE.** Replaced
  in place at the `S04_MERGE_CANONICALIZE` call site with an accurate one
  naming which fields are idempotent and which aren't, and pointing at B2's
  repair and this document.
- **Recommendation 3 (the S04/S06 skip, B4/B5) — DONE.**
  `discovery.reconstruct_merge_outcome` (read-only twin of
  `merge_and_canonicalize`) and a direct `Repo.get_shortlist` read-back,
  both gated on `resuming and repo.stage_succeeded(run_id, "<stage>")`
  exactly as Q2 specified, both reporting `"skipped": "resumed: already
  succeeded"` per Q3.
- **Recommendation 5 (the S09/S10/S12 reconciliation, B6/B7/B8) — DONE.** A
  `Repo.list_claims(run_id=run_id, status=...)` query for `VALIDATED` and
  `NEEDS_FOLLOW_UP`, unioned with the in-memory list, run unconditionally
  before S09 on every invocation, scoped to `run_id` only.
- **Q1's shared helper turned out to already exist** — `Repo.stage_succeeded`
  was already there (built for S01-S03's own resume checks) and needed no
  changes; only new call sites.

**Verified with the exact negative controls §5 and Q4 called for**, not
merely reasoned about — see CLAUDE.md's 2026-09-11 entry for what each test
proves and where it lives (`tests/test_merge_purpose_relevance.py`,
`tests/test_runner_e2e.py`). 1000 tests passing on SQLite (+20 skipped), up
from 994; no migration.

---

**Original status line, 2026-09-10 (superseded by the update above — kept per
GR-2): "Status: PLANNING, nothing built."** Written that day, prompted by the
owner's question during `Fuel_Cost_Stage_1` run 10's post-batch resume:
*"How could there be a direct resume after the batch is confirmed drained?"*
Extended the same day with a second, independently-discovered gap in the same
family — a resumed run that reported zero claims for a run that actually had
74 real, judged ones sitting in the database. Follows
[CLAUDE.md's BQRS shape](../../../CLAUDE.md#bqrs--the-required-shape-for-a-code-development-plan-standing-preference)
— the first document written to that template.

Every code fact and every measured number below was read or queried live
against the running codebase and the production database on 2026-09-10, not
recalled — see each Blocker for the exact query.

**Both problems share one shape, worth naming before the detail**: a resume
trusts something held in one process's memory instead of re-deriving it from
what the database actually holds. Part 2 (below) is that in-memory value
silently drifting from the truth (an accumulator re-summing itself). Part 3
is that in-memory value going missing entirely across a process boundary (a
claim-id list that dies with the process that built it). The fix for each is
different — one needs the stage to stop trusting a full recompute, the other
needs it to start trusting the database more than its own memory — but
neither is safe until "resume" stops meaning "re-derive everything from
scratch, in this process, right now."

---

## 1. The problem, in two parts

`perry run --variable X` (fresh or resumed) always walks
`runner.STAGE_ORDER` — the merge/canonicalize stage through finalize — in
order, on every invocation. There is no "read `research_run_stages`, skip
whatever already succeeded" shortcut anywhere in `_run_stages()`. Instead,
**each stage's own body decides internally how cheap re-execution is**:

- The query-plan, semantic-discovery, and lexical-discovery stages each check
  "did I already do this exact work for this run_id" and return in well under
  a second on resume (`'resumed': True` in their summaries).
- **The merge/canonicalize and shortlist stages have no such check.** The
  merge/canonicalize call site says so directly: *"Always safe to rerun:
  idempotent upserts over already-persisted search_results, no external
  calls."* That's a claim about correctness, not cost — and, as of tonight,
  it's also **wrong** for one of the three things it upserts.
- The acquire and claim-extraction stages skip per-item (document/queue-scoped
  resume guards), so they're fast on resume despite "always executing" too.

**Part 1 — cost.** On `Fuel_Cost_Stage_1` run 10's resume tonight, the
merge/canonicalize stage re-ran its full pass over the same 1,275
already-persisted search results and took the same order of magnitude as the
first pass (924s the first time; comparable again on resume). The shortlist
stage followed at 364s. That's roughly 21 minutes of wall clock spent
re-deriving a result that cannot have changed — nothing about draining a batch
touches discovery or ranking.

**Part 2 — correctness, found while investigating part 1.** The
merge/canonicalize stage's per-document write
(`Repo._upsert_variable_document_state`) accumulates one of its three fields
as a running SQL `+`:

```python
"relevance_score": tbl.c.relevance_score + relevance_delta,
```

`purpose` (monotonic max — never lowers) and `provider_score_best` (running
max, NULL-safe) are genuinely idempotent under an exact repeat. `relevance_score`
is not. **Verified live**, by independently recomputing the RRF sum from
`search_results_for_run(10)` from scratch (same formula, same grouping the
stage itself uses) and comparing to the stored `variable_document_state.
relevance_score` for all 882 rows belonging to variable 6:

```
n compared: 882
ratio (stored / freshly-recomputed): min 1.99999999..., max 2.00000000...9, median 2.0
histogram: {2.0: 882}
```

**Every single row is exactly double what one clean pass produces.** Tonight's
resume re-ran the merge/canonicalize stage's *own already-recorded
contribution* a second time and added it to itself — not new discovery, not a
different run finding the same document again (which is the legitimate case
this accumulator exists to handle), but the identical run_id's identical rows,
re-summed. A third resume would make it 3x.

**Part 3 — a second, independent gap, found the same day: a resumed run can
report zero claims for a run that actually has dozens, without losing or
rejecting a single one.** After the same run's batch was drained by a
*separate* `perry extract --worker` process (persisting 89 real claims — 47
`VALIDATED`, 27 `NEEDS_FOLLOW_UP`, 15 `QUARANTINED` — via `persist_extraction`,
each already correctly gated and judged), resuming with `perry run` reported:

```
S09_VALIDATE_CLAIMS   validated_claims: 0
S10_NORMALIZE         normalized: 0
S12_QUALITY_FEATURES  scored: 0
S14_COVERAGE_EVAL     review_ready_claims: 0, complete: False
Fuel_Cost_Stage_1: SUCCEEDED — Completion policy: NOT MET
```

**Every claim was still there, verified by direct query** — `evidence_claims`
for variable 6 still held all 89 rows, still tagged `run_id=10`, nothing
deleted or overwritten. The `0`s are a reporting/promotion gap, not data loss,
and it is the judge doing its job correctly upstream that makes this
confusing: it's easy to mistake "the run reports nothing" for "the judge
rejected everything," when the actual cause is three stages downstream of the
judge never running at all.

**Root cause, read directly from the code**: `S09`/`S10`/`S12` all iterate
one in-memory list, `validated_claim_ids`, built exclusively from
`_run_extraction`'s return value — itself built exclusively from
`drained.validated_claim_ids`, i.e. whatever *this specific process
invocation's own* drain touched (`runner.py`'s `_run_extraction`, lines
1215-1220). Tonight's `perry run` invocation's own extraction pass found only
4 leftover documents (all 0-claim), so its list was `[]`. The 89 claims a
*different* process had already persisted never entered it, because nothing
re-derives that list from the database — it is trusted, in full, from
whichever single process happened to build it.

**And `S12_QUALITY_FEATURES` is not merely a scorer — it is the *only* place
that promotes a claim from `VALIDATED` to `REVIEW_READY`** (its own module
docstring: *"S12 also performs the VALIDATED -> REVIEW_READY transition"*).
`Repo.review_ready_claims_detail` — what coverage, `perry status`, and the
review queue all read — matches only `REVIEW_READY`/`APPROVED_PRIMARY`/
`APPROVED_SUPPORTING`, never bare `VALIDATED`. So a claim `S12` never sees
is not just unscored — it is **permanently invisible to every human-facing
surface this project has**, no matter how correct its extraction and its
judge assessment were.

---

## 2. Blockers

**B1 — the accumulator's `+=` is only sound across *different* `run_id`s, and
nothing distinguishes that from "this run_id's own repeat."** WI-9/GR-3
deliberately made `relevance_score` a sum: a document found again by a *later*
run's queries earns more accumulated relevance, and that's real signal. But
the SQL has no way to tell "run 7 found this too" from "run 10 found this
again because run 10 re-executed." A stage-succeeded skip (§3 below) fixes the
`perry run` resume path specifically — it's necessary and sufficient there —
but does not, by itself, make `_upsert_variable_document_state` sound against
some *other* future re-entry path that isn't mediated by the same check.
**Recommendation: build the skip (it is both the performance fix and the
correctness fix for the one path that's actually exercised today), and
separately correct the call-site comment**, which currently asserts a false
safety property for all three fields when it's true of only two. A comment
asserting something false is worse than no comment — this project has paid for
that shape before (`worldnuclearnews.org`, `committed_estimate`).

**B2 — the live corruption already exists and needs repair independent of
everything else in this plan.** `variable_document_state.relevance_score` for
all 882 rows tied to variable 6 (`Fuel_Cost_Stage_1`) is in production, right
now, at 2.0x its correct value, and will compound to 3x/4x on any further
resume before a fix ships. **Recommendation: repair immediately, as its own
small change, not gated on §3 landing.** Recompute from
`search_results_for_run(run_id)` fresh rather than dividing every value by
2 — a divide is only correct if exactly one extra pass happened, and a second
accidental resume before the repair ships would make that assumption wrong.
The repair script should reuse the exact recomputation used to detect this
(URL-normalize each search result, sum RRF contributions per document, join
through `source_document_urls`) and overwrite `relevance_score` per row.
Verify the same way detection did: query 2 above must read 1.0x after.

**B3 — does this actually threaten tonight's shortlist result?** Checked, not
assumed, by reading `perry/coordinator/shortlist.py::resolve_relevance_value`:
it returns `provider_score_best` whenever `use_provider_score` is set *and*
the candidate's `provider_score_best is not None`, falling back to
`relevance_score` only otherwise. `use_provider_score` is keyed on
`SearchRole.SEMANTIC` (true for this variable), and Exa's adapter never
emits `None` for `provider_score_best` — it falls back to the result's own
`.score` when no highlight is present, never to `0` or `None`
(`semantic_ranking_upgrades_v2.md`). So for `Fuel_Cost_Stage_1`, 0 of 882
candidates ever read the corrupted field, and tonight's already-computed
shortlist is unaffected. **Recommendation: state this as a checked fact, not
an assumption, precisely because a wrong answer here would have made a real
bug read as harmless.** It does not generalize — **any lexical-role variable
resumed the same way has no such immunity**, since `relevance_score` (RRF) is
that role's *primary* signal, not a fallback. Confirm this same check before
trusting "it's fine" on the first lexical-role variable that hits this path.

**B4 — `variable_document_state` is not run-scoped, so "read the merge stage's
output back" cannot mean "read `variable_document_state` for this variable."**
The table is a deliberate whole-variable accumulator (a document discovered
only by an *earlier* run legitimately has a row there too), so naively reading
it back on resume would silently widen this run's document pool to include
documents this run never touched. **Recommendation: reconstruct exactly what
the merge stage already returns today — the run-scoped document id set — from
`search_results_for_run(run_id)` (already scoped by `run_id` via
`retrieval_events`/`search_queries`), but as a *read-only* pass**:
URL-normalize each row and look up its existing `source_document_id` via
`source_document_urls` (no upserts, no writes) rather than the current
read-write pass through `upsert_source_document_with_state`/
`record_variable_document_state`. Every document this run discovered already
exists as a row by the time a resume happens (this run created them the first
time through), so the lookup half is guaranteed to hit; only the accumulating
write half needs to be skipped. No schema change.

**B5 — can the shortlist stage's result be read back, or does it also need a
read-only recomputation?** Simpler than B4: `shortlist_entries` already
persists rank and score per run for every candidate, not only the selected
ones (`politeness_and_topup_fix.md`, 2026-08-07 — "the ranked reserve was
being thrown away" fix made this true). **Recommendation: a stage-succeeded
skip for the shortlist stage reads the persisted `shortlist_entries` for this
`run_id` back directly — no recomputation of any kind, not even a read-only
one.**

**B6 — the fix for Part 3 must re-derive the claim-id list from the database,
not grow the in-memory one.** Extending `validated_claim_ids` with more
in-process bookkeeping cannot help — the defining fact of this bug is that a
*different process* wrote the claims, so no amount of care inside one
process's own accumulation closes the gap. **Recommendation: before S09/S10/
S12 run, query the database directly for every claim belonging to this
`run_id` whose status is `VALIDATED` or `NEEDS_FOLLOW_UP`**
(`Repo.list_claims(run_id=run_id, status=...)`, looped over those two
statuses — the exact call `perry rescore` already makes today, scoped there
to `variable_id` for its own cross-run purpose; here scoped to `run_id`), and
**union those ids with whatever this invocation's own extraction pass
produced**, deduplicated, before feeding the combined list to S09/S10/S12.
`Repo.list_claims` already accepts `run_id` — no new query surface needed,
only a new call site.

**B7 — should this reconciliation run on every invocation, or only when a
resume is detected?** **Recommendation: unconditionally, every time, fresh
run or resumed — and notice this is the *opposite* shape from B1-B5's fix.**
Those are about *skipping* expensive, already-correct recomputation (S04/S06
over an 882-document pool). This is about *always performing* a cheap,
already-idempotent DB query that the current code skips only because it
wrongly trusts an in-memory list instead. `compute_and_persist_quality` is
genuinely idempotent — re-running it on an already-scored claim recomputes
the identical vector and overwrites the identical row — and claim volumes are
"dozens... per variable" (`review_ready_claims_detail`'s own comment), so
there is no meaningful cost to checking always. Trying to detect precisely
*when* a reconciliation is needed (a resume? a crashed process? a
manually-drained batch?) is a harder and more fragile problem than "always
check, cheaply" — and every case that shape would need to enumerate is a case
this recommendation makes irrelevant to enumerate.

**B8 — scope: this `run_id` only, never the whole variable.** Reaching across
*every* run of a variable on every `perry run` invocation would blur a
boundary this project draws deliberately: S12's own module comment states
*"S12 scores only the claims of the run that produced them"*, precisely so
that reaching back across runs — to apply a changed `evidence_status_weights`
or a rubric bump — stays `perry rescore`'s explicit, separately-invoked job,
never something `perry run` does as a side effect of resuming. **Recommendation:
scope B6's reconciliation query to `run_id`, matching S12's existing design
intent exactly — heal what *this* run stranded, and leave every other run's
claims for `perry rescore` to reach on purpose.**

---

## 3. Questions

**Q1 — a shared helper, or a bespoke check per stage?** → **Shared.** The
merge/canonicalize and shortlist stages are the two known cases today, but any
future stage that lacks an internal per-item resume guard will reproduce the
identical waste (and, if it writes an accumulator like B1's, the identical
correctness risk). A one-line `already_succeeded(repo, run_id, stage_name) ->
bool` — the same check the query-plan stage already does inline, generalized
— makes adding the guard to a third stage a one-line change instead of a
second hand-rolled implementation, the same reasoning that put
`extraction_policy.py`'s "one predicate, three consumers" module in place.

**Q2 — when does the skip apply?** → **Exactly where `resumed`/`already` is
already computed for the query-plan and discovery stages today — same
call site, same boolean.** `--fresh` starts a new `run_id`, so no
`SUCCEEDED` row exists yet for it and the check is naturally a no-op.
`--continue` already substitutes its own `pool_only` branch for both stages
(the existing `if pool_only:` blocks) — this plan doesn't touch that path at
all, only the ordinary resume path those branches currently have no bearing
on.

**Q3 — does a skipped stage need special handling in the run report or
`perry status`, so a near-zero duration doesn't read as suspicious?** → **No
new mechanism — reuse the existing shape.** Give the skipped stage's summary a
`"skipped": "resumed: already succeeded"` key, exactly the string shape
`pool_only`'s own skip message already uses. A reader sees an explicit reason,
not an unexplained duration that looks like a stage silently did nothing.

**Q4 — how should B6/B7's fix be verified, given the bug only appears across
*two separate process invocations*, which a single test function doesn't
naturally model?** → **Simulate the process boundary directly, and control
it.** Persist a claim via `persist_extraction` (or the repo call it makes)
exactly as the standalone worker would, entirely outside any call to
`_run_stages`/`_run_extraction` — this is "process A already ran." Then
invoke the S09-S14 portion of the coordinator for that same `run_id` with an
*empty* freshly-extracted list — this is "process B resumes and finds nothing
new to extract." Assert the claim is scored, promoted to `REVIEW_READY` (if
`VALIDATED`), and counted by coverage. **The negative control is reverting
B6's reconciliation call** — with it removed, this exact test must fail with
`scored: 0`/`review_ready_claims: 0`, reproducing tonight's live behavior
precisely rather than a constructed stand-in for it.

---

## 4. Recommendations (consolidated)

1. **Repair the live corruption now** (B2) — a standalone, small,
   database-only change; not gated on anything else here.
2. **Correct the false "idempotent" comment** at the merge/canonicalize call
   site now (B1) — one line, zero risk, no reason to wait.
3. **Build a shared `already_succeeded` skip helper** (Q1) and wire it into
   the merge/canonicalize stage (via the read-only, run-scoped reconstruction
   in B4) and the shortlist stage (via the direct `shortlist_entries`
   read-back in B5), gated exactly where the existing resume checks already
   are (Q2).
4. **Report every skip explicitly** in the stage summary (Q3).
5. **Add the run-scoped database reconciliation before S09/S10/S12** (B6),
   scoped to `run_id` (B8), run unconditionally on every invocation rather
   than only on a detected resume (B7), and verified with the
   process-boundary simulation and its negative control (Q4).
6. **Run `perry rescore --variable Fuel_Cost_Stage_1 --project nbc` now, on
   live data, independent of when items 1-5 ship.** It is the existing,
   already-built repair for exactly Part 3's stranded-claim shape (built
   2026-08-09 for the same failure mode via `reextract`) — `RESCORABLE_
   STATUSES` already includes `VALIDATED` and `NEEDS_FOLLOW_UP`, so it will
   score and promote all 74 of variable 6's stranded claims immediately, the
   same way the manual `rescore` step already does for every prior instance
   of this bug shape. Recommendation 5 stops the *next* run from stranding
   claims in the first place; it does nothing for the 74 already stranded
   tonight.

## 5. Sequencing recommendation

- **Run `perry rescore --variable Fuel_Cost_Stage_1 --project nbc` immediately**
  (recommendation 6) — needs nothing else in this document, fixes the live
  symptom the owner actually hit, and is safe to run before, during, or after
  everything else here lands.
- **B2's repair is urgent and independent — do it next, on its own.** It
  needs no migration, no spec change, no `spec_version` bump; it's a targeted
  database write, verified against the same read-only recomputation that
  found the problem.
- **B1's comment fix travels with B2's repair** — same small change, same
  false assumption.
- **The two mechanism fixes (Part 2's skip, Part 3's reconciliation) are
  independent of each other and can land in either order or together** — they
  touch different stages (merge/shortlist vs. validate/normalize/quality) and
  fix different failure shapes (an accumulator that shouldn't repeat vs. a
  list that should be re-derived, not trusted). Landing them in the same
  change is reasonable since both were found in one sitting and both are
  "resume correctness" in the same document, but neither blocks the other.
- **Both need an executed negative control before either is trusted**: Part
  2's skip needs the control in §5's original text (relevance_score must not
  move on a second resume); Part 3's reconciliation needs Q4's process-
  boundary simulation (stranded claims must be found and promoted with the
  fix in place, and the same test must fail with it reverted).
- **Land the skip mechanism (Part 2) before either of these two situations
  recurs**: a semantic-role batch variable that needs more than one resume
  (this run is the first example, and won't be the last — long
  native-ingestion batches make multi-resume runs routine, not exceptional),
  and — with higher priority, since it has no `provider_score_best`
  immunity — the next time any **lexical-role** variable's run is resumed
  after stopping mid-way. That case has never happened yet; it should not be
  allowed to happen before this lands, since there the corruption would
  change which documents actually get shortlisted, not merely inflate an
  unread column.
- **Land the reconciliation (Part 3) before the next time extraction is
  drained by a standalone `perry extract --worker`/`perry acquire --worker`
  process followed by a `perry run` resume of the same variable** — exactly
  tonight's sequence, and the CLAUDE.md-documented, intended way to use those
  commands ("long-lived processes alongside `perry run`"), so this is not an
  edge case to deprioritize; it is the normal operating pattern for any
  large-batch semantic run, and it will recur on the very next one unless
  this lands first.
---

<!-- Relocated verbatim from CLAUDE.md on 2026-09-14 (journal/misc/claudemd_redesign.md). -->

## A resume no longer re-derives everything from scratch in one process (2026-09-11)

**1000 tests passing on SQLite (+20 skipped)**, up from 994. **No migration**
— every fix touches only in-process control flow and existing tables.
Design record, approved by the owner the same day:
[`resume_stage_shortcuts.md`](journal/v0-6/refactoring/resume_stage_shortcuts.md)
(the first document written to the BQRS template above). Found and fixed in
one sitting, prompted by a direct question during `Fuel_Cost_Stage_1` run
10's post-batch resume: *"How could there be a direct resume after the batch
is confirmed drained?"*

**Two data-correctness repairs, done live before any code shipped.**
`variable_document_state.relevance_score` for all 882 rows tied to variable 6
was found at exactly 2.0x a fresh recomputation (a resumed run had re-run
S04's accumulating write over the same already-persisted search results) —
repaired by overwriting from a fresh one-pass recomputation, re-verified at
exactly 1.0x. Separately, `perry rescore --variable Fuel_Cost_Stage_1` was
run to recover 47 claims stranded at `VALIDATED` (unpromoted, unscored,
invisible to coverage) by the second bug below, before either mechanism fix
existed — the existing repair command for exactly this shape, built
2026-08-09 for an unrelated incident (`reextract`).

**Fix 1 — `S04_MERGE_CANONICALIZE` and `S06_SHORTLIST` skip on resume.**
Neither stage had a "did this already succeed" check the way S01-S03 already
did — both always recomputed, at real cost (924s + 364s on an 882-document
pool) and, for S04, real risk: `Repo._upsert_variable_document_state`
accumulates `relevance_score` as a running SQL sum, sound across *different*
runs finding a document again, unsound against the same `run_id`'s own
repeat. `discovery.reconstruct_merge_outcome` is S04's read-only twin —
same URL-normalize-and-look-up logic, `find_document_by_normalized_url`
only, no upserts — used when `Repo.stage_succeeded(run_id,
"S04_MERGE_CANONICALIZE")` is true on a resume. S06 needs no recomputation
at all: `shortlist_entries` already persists rank and score for every
candidate, not only the selected ones (2026-08-07's "ranked reserve" fix),
so its skip just reads them back. Both report `"skipped": "resumed: already
succeeded"` in their stage summary, the same string shape `--continue`'s own
skip already uses.

**Fix 2 — S09/S10/S12 reconcile their claim-id list against the database on
every invocation, not only the in-memory one `_run_extraction` built.**
`validated_claim_ids` was exclusively whatever *this process invocation's
own* extraction pass touched. Draining a batch via a standalone `perry
extract --worker` (a different process from the `perry run` that later
resumes) persists real, judged claims that never enter that list — and
`S12_QUALITY_FEATURES` is the *only* place that promotes `VALIDATED` ->
`REVIEW_READY`, so a claim it never sees is permanently invisible to
coverage, `perry status`, and the review queue, with zero data loss and zero
error anywhere. Fixed by unioning the in-memory list with a direct query —
`Repo.list_claims(run_id=run_id, status=...)` for `VALIDATED` and
`NEEDS_FOLLOW_UP` — run unconditionally every time, not gated on a detected
resume: `compute_and_persist_quality` is genuinely idempotent and claim
volumes are small, so "always check, cheaply" beats trying to enumerate
every path that could strand a claim. Scoped to `run_id` only, matching
S12's own existing design intent ("S12 scores only the claims of the run
that produced them") — reaching across every run of a variable stays `perry
rescore`'s separate, deliberately-invoked job.

**One deliberate, small widening beyond pure stranding-repair, worth
knowing.** `persist_extraction` only ever appended a claim id to its return
list when `status == "VALIDATED"` — never `NEEDS_FOLLOW_UP`, by design, in
*every* run to date, not only a resumed one. Including `NEEDS_FOLLOW_UP` in
Fix 2's reconciliation (matching `perry rescore`'s own `RESCORABLE_STATUSES`)
means every run now scores its own `NEEDS_FOLLOW_UP` claims inline, where
previously that required a later manual `rescore` — the same population
`RESCORABLE_STATUSES` already treated as legitimate to score, now reached
without a human asking a second time.

**Verified with executed negative controls, not reasoned about.** A
primitive-level test (`tests/test_merge_purpose_relevance.py`) pins that
calling `merge_and_canonicalize` twice really does double `relevance_score`
— the fact that justifies the skip existing at all, kept as a permanent
regression pin independent of the skip. Two runner-level tests
(`tests/test_runner_e2e.py`) crash a fixture run *after* S04/S06 genuinely
succeed, resume it, and assert `relevance_score` is unchanged / that
`build_shortlist` is never called a second time (wired to raise if it is).
A third reproduces Fix 2's exact live shape — a real `VALIDATED` claim left
by one invocation, a second invocation whose own extraction pass finds
nothing new — with the reconciliation monkeypatched away first as the
negative control (the claim stays `VALIDATED`, unscored, reproducing the
historical bug precisely) before being restored and shown to heal it.

**Still open:** the Postgres fixture (`docker-compose.test.yml`) was not run
this session — nothing here is Postgres-specific SQL, but it hasn't been
checked; and the false "idempotent" comment at the old S04 call site was
corrected in place rather than merely removed, so a reader who has the old
line memorized should re-read it.


