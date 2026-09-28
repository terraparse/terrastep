---
status: implemented
status_changed: 2026-09-15
type: legacy
---

# S3 layout split: `source/`, `reading/`, `reports/` under `perry/`

**2026-09-15.** Follows from the perry-web S3 credential work
(`journal/perry-web/perry-web_combined_handoff_2026-09-04_to_09-14.md` §2,
`aws/README_perry_web_s3_credential.md`): the drafted read-only IAM policy
originally scoped `s3:GetObject` to the whole `perry/*` prefix, which also
covers run reports — an object family perry-web never fetches. Rather than
carry that extra reach indefinitely, or invent a filename-suffix rule for the
IAM policy to match, three of Perry's own object families get their own
subdirectory under `perry/`, so the IAM resource ARN can name exactly the two
perry-web needs.

## What changed

`perry/storage/s3.py`'s three key-builder functions each gained one new
leading path segment:

| Object family | Old key | New key |
|---|---|---|
| Source documents | `perry/{project_id}/{variable_id}/{run_id}/{sha256}/{filename}` | `perry/source/{project_id}/{variable_id}/{run_id}/{sha256}/{filename}` |
| Run reports | `perry/{project_id}/{variable_id}/{run_id}/{filename}` | `perry/reports/{project_id}/{variable_id}/{run_id}/{filename}` |
| Reading list | `perry/{project_id}/{variable_id}/{filename}` | `perry/reading/{project_id}/{variable_id}/{filename}` |

This is a **considered repeat** of the move `project_identifiers.md` B5 already
made once (variable-name-keyed → id-keyed prefixes): a top-level key-scheme
change, landing as a code change plus a separate migration pass over existing
objects, not a live rewrite.

## Blockers

**B1 — Does anything else read or write the four `source_document_versions`
URI columns besides `acquire.py`'s initial insert?** If something else
updates `original_artifact_uri`/`firecrawl_response_uri`/
`parsed_markdown_uri`/`tables_markdown_uri` after row creation, a migration
script racing that writer could silently revert a completed move or update a
stale row.

*Checked, not just assumed*: grepped `perry/db/repo.py`, every
`coordinator/stages/*.py`, and `cli.py` for assignments to all four column
names — the only writer is `acquire.py:547-580`, at insert time, never
touched again. **No blocker.** The one live race this leaves is a fresh
acquisition landing under the *old* flat scheme if it runs between deploying
this code change and running the migration script — self-healing, since the
migration script is idempotent (skips anything already under `source/`) and
just needs a second pass.

**B2 — What identifies a source-document object, given the bucket also holds
objects from an *earlier* key-scheme migration (`project_identifiers.md`
B5's variable-name-keyed prefix, never rewritten per that doc's own note)?**
Getting this wrong means either missing old-scheme documents entirely, or
misclassifying a reading-list/run-report object as a source document.

**Recommendation: drive the source-document pass from the database, not from
listing S3.** `source_document_versions`'s four URI columns already hold each
document's exact current key, whichever scheme wrote it — no need to
distinguish schemes by parsing the bucket. The transform is uniform
regardless of vintage: take the stored key, insert `source/` immediately
after the `perry/` prefix segment, copy, verify, update the column, delete
the old object. This sidesteps B2 rather than solving a parsing problem.

**B3 — Reading lists and run reports have no DB-stored key at all** (checked:
no column anywhere stores either), so they can't be migrated the same way.
**Recommendation:** drive this pass from an S3 listing instead, sorted by
filename suffix — `..._reading_list.json` (`reading_list.py:40-43`) vs.
`..._run_report.json` (`run_report.py:152-164`) are the only two shapes,
confirmed by grepping every `put_bytes`/`put_json`/`put_text` call site in
production code (`s3.py`, `acquire.py`, `run_report.py`, `reading_list.py` —
nothing else writes under `perry/`). Extension does **not** discriminate —
run reports are JSON-only in S3 (the Markdown rendering only ever reaches a
local mirror, never `s3.put_*` — checked `run_report.py:558-567`) — so both
remaining families are `.json` and must be told apart by filename suffix, not
extension. Any object matching neither suffix, and not present in the
DB-driven source-document key set, is genuinely unrecognized and must be
reported, not guessed at or silently skipped.

## Questions

**Q1 — Should the "not moved" final count lump unrecognized objects together
with objects that were recognized but failed mid-copy?**

**Recommendation: no, report them as two separate counters.** They have
different fixes — an unrecognized object needs a human to look at what it
actually is; a failed copy needs a retry of the same, already-understood
operation. Collapsing them into one number would hide which situation
applies. (Owner confirmed this recommendation in conversation before the
script was written.)

**Q2 — Dry-run first, or one live pass?**

**Recommendation: dry-run by default, live only behind an explicit
`--execute` flag**, matching the verification discipline
`perry_web_role.sql`'s own history already established for this project
("verifying a grant file means running it, not diffing it" —
`aws/README_perry_web_s3_credential.md`). A dry run only lists and classifies
(`list_objects_v2`/`head_object`/DB `SELECT`) — no `copy_object`,
`put_object`, `delete_object`, or `UPDATE`. (Owner confirmed this
recommendation in conversation before the script was written.)

## Recommendations

- Drive the source-document pass from `source_document_versions`'s four URI
  columns, not from listing S3 (B2).
- Drive the reading-list/run-report pass from an S3 listing, sorted by
  filename suffix, not extension (B3).
- Report "not moved" as two separate counters: unrecognized objects, and
  recognized-but-failed operations (Q1).
- Default to dry-run; require `--execute` for the live pass (Q2).
- Order per object, always: copy → verify (`head_object` `ContentLength`
  match) → (source documents only) commit the DB `UPDATE` → delete the old
  object. Never delete before the new copy is verified and, for source
  documents, the DB row repointed — a crash mid-run must leave a
  still-reachable document, never an orphaned DB row.

## Sequencing recommendation

1. Ship the `perry/storage/s3.py` code change (this commit) — new writes go
   straight to the new layout immediately, with no coordination required,
   because B1 established there's no concurrent writer to race.
2. Run the migration script (`scripts/s3_layout_migration/`) in dry-run mode
   first against the live bucket/DB; review the printed counts, especially
   the unrecognized-object list, before doing anything destructive.
3. Run it with `--execute` once the dry-run output looks right.
4. Only after that: narrow `aws/perry_web_s3_readonly_policy.json` to
   `perry/source/*` and `perry/reading/*` (dropping the flat `perry/*` grant
   and `reports/` entirely) and apply it per
   `aws/README_perry_web_s3_credential.md`'s existing Option A/B steps —
   this step must land **after** the migration, not before, or perry-web's
   grant would stop resolving keys that haven't moved yet.

This does not need to be bundled with, or block, any other in-flight
refactoring — it touches only `perry/storage/s3.py`'s three key-builder
functions, a new standalone script, and the not-yet-applied IAM policy draft.

## 2026-09-15 execution note: the move completed, cleanup did not

`scripts/s3_layout_migration/01_migrate.py --execute` ran against the live
bucket and database. Copy, verification, and the `source_document_versions`
DB update all succeeded for every object (confirmed by direct query
afterward: 0 of 279 non-null-URI rows still point at the old scheme). The
final `delete_object` on each old key failed for all ~779 objects —
`perry-pipeline-s3` has no `s3:DeleteObject` permission. This is a
credential-scope fact, not a script defect; see
[`aws/s3_resource_path_fix_cleanup_todo.md`](../../../aws/s3_resource_path_fix_cleanup_todo.md)
for the full account, why a straight script re-run won't fix it, and how to
find the leftover duplicates once a delete-capable credential exists.
Sequencing step 3 (apply the narrowed perry-web IAM policy) is unaffected —
it only depends on the new-location copies existing, which they do.
