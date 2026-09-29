# Sharing terrastep: setup and maintenance

A plain guide, not a proposal: it carries no frontmatter on purpose, because it does not sit in a
designated `scan_dirs` directory (same reasoning as `terrastep_101.md`). It assumes you've read
that doc; this one is about getting terrastep *to* a project and keeping it current there, not
what terrastep checks once it's there.

## 1. Getting terrastep ready for easy project-by-project installation

This section is a checklist; items are marked done as they happen, not all done up front.

1. **Add a `LICENSE` file. Done (2026-09-28), MIT.** `pip` and GitHub both read it; without it,
   the terms anyone installing terrastep is operating under are undefined.
2. **Add license/author metadata to `pyproject.toml`. Done (2026-09-28)**: `license = {file =
   "LICENSE"}`, `authors`, and an OSI classifier. Still open: a `[project.urls]` table
   (`Repository`, maybe `Issues`) — needs (3) to exist first, so there's a URL to point at.
3. **Push this repository to a public GitHub remote.** Today `git remote -v` is empty — this repo
   has never been pushed anywhere. Once it has a remote:
   ```
   pip install git+https://github.com/<you>/terrastep.git
   ```
   works from any machine, no auth, no cloning by hand — this alone satisfies "easy
   project-by-project installation" for anyone who already has your URL.
4. **Optional, but worth it for "easy"**: publish to PyPI. `pip install terrastep` (no URL, no
   `git+`, and `pip install --upgrade terrastep` for updates) is a meaningfully lower-friction
   experience than a git URL, and is what most people expect. Needs: (1) and (2) done first, a
   PyPI account, `python -m build` (produces `dist/*.whl` and `dist/*.tar.gz`), then
   `twine upload dist/*`. A name squat check on PyPI for `terrastep` is worth doing before
   committing to the name publicly. This is a bigger step than (3) — a published package name is
   hard to walk back — so treat it as a separate decision, not a default.
5. **Decide the version-tag convention** before the first real release, not after. Recommended,
   absent a stronger reason: [SemVer](https://semver.org/) — a MAJOR bump for any change that could
   make an already-passing document start failing `terrastep check` (a new required field, a
   stricter rule), MINOR for a new verb or config key that doesn't change existing behavior, PATCH
   for a bug fix. `terrastep` has no automated migration between versions yet (0001, "What this
   does not do") — a MAJOR bump is exactly the kind of change that would need a hand-written note
   like the Perry handoff (`journal/perry_terraparse_handoff.md`-style) until that tooling exists.
6. **Tag releases in git**: `git tag vX.Y.Z && git push --tags`, once (3) is done. Lets a consumer
   pin `pip install git+https://github.com/<you>/terrastep.git@v0.1.0` instead of always floating
   on the tip of `main`.

None of steps 3-6 are reversible the same way a local commit is (a public push, a published
package name, a pushed tag are all visible to others once done) — confirm before running them, not
after.

## 2. Adopting terrastep in a new repository (once 1 is done)

This is the sequence for a consumer — could be you, in a different project, or someone else
entirely:

```
pip install terrastep                      # or: pip install git+https://github.com/<you>/terrastep.git
```

Then, at that repo's root:

1. Write a `terrastep.toml` naming `scan_dirs` (see `terrastep_101.md`'s Config table for every key).
2. If there's existing undocumented markdown to bring under the format:
   `terrastep migrate propose`, review the table by hand, `terrastep migrate apply`.
3. `terrastep build && terrastep check` — confirm it's clean.
4. `terrastep install-hooks` — the pre-commit hook that blocks a bad staged commit.
5. `terrastep skill install` — the Claude Code skill, written to
   `.claude/skills/terrastep/`. Commit it (it's typically small, and committing it is what makes
   the skill available to anyone else who clones the repo, without them running this step
   themselves).
6. Commit `terrastep.toml`, the index file, and the installed hook/skill state together.

Every step here is already covered, in more depth, by `terrastep_101.md`'s "How to use them" and
`readme.md`'s short version — this section exists to give the *adoption sequence specifically*,
start to finish, in one place, rather than assuming someone stitches it together from two other
docs.

## 3. Maintaining terrastep as the codebase changes and new versions ship

A release is not just "bump the version number." In order:

1. **Make the actual code change** in `core.py`/`config.py`/`cli.py`/etc., with its own tests
   passing.
2. **Bump `terrastep.__version__`** in `src/terrastep/__init__.py` — the single source of truth
   (`pyproject.toml` reads it dynamically; see `CLAUDE.md`'s "Versioning and the generated
   docs/skill"). Decide the bump size using the SemVer convention from section 1, step 5.
3. **Regenerate the generated docs and skill**: `venv/bin/terrastep skill build`. This is not
   optional and not separable from step 2 — every generated file (`journal/terrastep_101.md`,
   `src/terrastep/skill/**`) stamps the version that produced it, so a version bump is a content
   change to all of them. `CLAUDE.md` already says this; repeated here because it's the step most
   likely to be forgotten under release pressure.
4. **Refresh this repo's own dogfooded copy**: `venv/bin/terrastep skill install --root . --force`.
5. **Run the full suite**: `venv/bin/python -m pytest -q tests`. Specifically watch
   `test_skilldoc.py::test_checked_in_generated_files_are_not_stale` — it's the guard for step 3,
   but don't rely on it catching a skipped regenerate; do step 3 deliberately.
6. **Run `terrastep check`** on this repo's own `journal/plans/` — a release should not leave
   terrastep's own journal failing its own check.
7. **Commit the version bump and the regenerated files together**, one commit — they're one
   logical change, not two.
8. **Tag and push** (`git tag vX.Y.Z && git push --tags`), once section 1's steps 3 and 6 are done.
9. **If published to PyPI**: `python -m build`, `twine upload dist/*`.

### What a consumer does after a new version ships

- `pip install --upgrade terrastep` (or re-pin the git tag).
- **Re-run `terrastep skill install --root . --force`** in every repo that has the skill installed.
  Nothing pushes an update to an already-installed skill automatically — `.claude/skills/terrastep/`
  is a snapshot from whenever it was last installed, not a live link to the package. The
  `terrastep_version:` field in that repo's `SKILL.md` frontmatter is how you'd notice it's stale
  (by comparing it to `terrastep.__version__` in the newly installed package) — there is no
  automated check for this yet (Q5, 0002: recording the version was in scope; detecting a mismatch
  was explicitly deferred).
- `terrastep build && terrastep check` — confirm the upgrade didn't newly fail anything. A MAJOR
  version bump is exactly the case where it might; there's no migration tool yet (see section 1,
  step 5), so a failure here means reading the release's notes and fixing documents by hand.

### What this guide does not solve

- **No automated version-mismatch detection** between an installed skill and the `terrastep`
  package that's actually running (0002, Q5). The version is recorded; nothing reads it back yet.
- **No automated migration between terrastep versions** (0001, "What this does not do"). A
  breaking rule change needs a hand-written migration note per consumer, the same shape as the
  Perry handoff, until that tooling exists.
- **No CI.** Every check in section 3 above is run by hand, by whoever is doing the release. There
  is no automated release pipeline yet.
