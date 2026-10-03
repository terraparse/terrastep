# Sharing terrastep: setup and maintenance

A plain guide, not a plan: it carries no frontmatter on purpose, because it does not sit in a
designated `scan_dirs` directory (same reasoning as `terrastep_101.md`). It assumes you've read
that doc; this one is about getting terrastep *to* a project and keeping it current there, not
what terrastep checks once it's there.

**Updated 2026-09-30** for the actual near-term need: sharing terrastep with other repositories
you develop with Claude Code, most of which sit on this same machine
(`/home/jga/dev/3p/atomicalc`, `ebow`, `perry-web`, `tmdc-web` today). That need does not require
GitHub, a public repository, or PyPI — pip installs directly from a local directory, no network
involved. Verified today: both a regular and an editable local install expose the `terrastep`
command and correctly locate the bundled skill (`terrastep skill install` copies it out), with
`git remote -v` still empty.

**Update 2026-10-01**: method B is also done now. `origin` is
`https://github.com/terraparse/terrastep.git` (public), with `main`, `dev`, and the `v0.2.0`
annotated tag all pushed. The checklist in method B below is updated to say so; the mechanics stay
useful for the next new branch or tag.

## The three ways to share it, and which to use

| Method | Needs | Best for |
|---|---|---|
| **A. Local path** | Nothing beyond this checkout. | Repos on this machine — the actual case today. |
| **B. A git remote** | A GitHub repo, public or private. | A repo on another machine, or another person. |
| **C. PyPI** | (A) or (B) already done, a PyPI account. | Convenience once/if this is ever public. |

None of these are mutually exclusive, and none is a prerequisite for another. Start with A; move
to B only when a repository genuinely isn't on this filesystem; C is a later, separate decision
(a published package name is hard to walk back — see its own note below).

### A. Local path (recommended today)

No setup. From any other repo's own virtualenv:

```
pip install /home/jga/dev/3p/terrastep              # a stable snapshot
# or
pip install -e /home/jga/dev/3p/terrastep           # a live link to this working tree
```

Both were verified to work end to end just now: `terrastep skill install`, `terrastep build`,
`terrastep check` all ran correctly against a fresh scratch repo, from each install.

**Regular vs. editable:** a regular install copies the package at install time; the consumer
repo's `terrastep` is frozen until someone reinstalls it. An editable install (`-e`) links back
to *this* checkout — the next time that repo runs `terrastep`, it runs whatever is on disk here
right now, no reinstall step. While terrastep is still changing every session (0001 through
0007 so far), editable is the lower-friction choice for your own repos; use a regular install
only where you want a pinned, won't-move-under-me copy.

**What does not change, either way:** `terrastep skill install` always *copies* the bundled skill
into the consumer repo's `.claude/skills/terrastep/` — even under an editable install. A later
change to the skill's content still needs `terrastep skill install --force` run again in that
repo. Only the CLI's behavior is live-linked by `-e`; the installed skill snapshot is not.

**No version pinning is possible this way** — a local path always means "whatever is on disk right
now." If a consumer needs to freeze to a specific point, tag a commit here (`git tag vX.Y.Z`) as a
record, but there is nothing to `pip install` against a local tag; that pinning only exists once
there's a remote (B) to check the tag out from, or a built wheel copied over by hand.

### B. A git remote

Needed only once a repository you want to share with is not reachable from this filesystem. The
remote does **not** need to be public:

```
pip install git+https://github.com/<you>/terrastep.git            # public repo, or private with a token
pip install git+ssh://git@github.com/<you>/terrastep.git          # private repo, SSH key auth
```

Checklist, done once:

1. **License file and metadata. Done (2026-09-28).** MIT, `LICENSE`, and `pyproject.toml`'s
   `license`/`authors`/classifier. Needed regardless of public or private — without it, the terms
   anyone installing terrastep operates under are undefined.
2. **Push to a GitHub remote. Done (2026-10-01).** `origin` is
   `https://github.com/terraparse/terrastep.git`, public. `main` and `dev` are both pushed and
   tracking (`git branch -vv` shows `[origin/<branch>]`). A private repository would have been an
   equally adequate choice for "share with my other repos, or a collaborator" — it only costs the
   puller needing read access (an SSH key registered with GitHub, or a personal access token); going
   public was a separate decision, made here, not a requirement of method B itself.

   A new local branch still needs one `git push -u origin <branch>` to start tracking (plain
   `git push` fails for a branch the remote has never seen); after that first push, plain `git push`
   / `git pull` work on it with no flags.
3. **Decide the version-tag convention** before the first tag, not after. Recommended, absent a
   stronger reason: [SemVer](https://semver.org/) — MAJOR for a change that could make an
   already-passing document start failing `terrastep check`, MINOR for a new verb or config key
   that doesn't change existing behavior, PATCH for a bug fix. terrastep has no automated migration
   between versions yet (0001, "What this does not do") — a MAJOR bump needs a hand-written
   migration note per consumer (the shape of `journal/origin/handoff.md`) until that tooling
   exists.
4. **Tag releases**: `git tag -a vX.Y.Z -m '<message>'` (an *annotated* tag — plain `git tag
   vX.Y.Z` makes a lightweight tag with no message and no date, worth avoiding for a release marker),
   then push the branch and the tag together with `git push --follow-tags`. `--follow-tags` pushes
   only annotated tags reachable from what you're pushing, so it's safe to run routinely without
   risk of pushing some unrelated stray tag — unlike `git push --tags`, which pushes every tag in the
   repo regardless of reachability or annotation. Lets a consumer pin
   `pip install git+https://github.com/<you>/terrastep.git@v0.1.0` instead of floating on `main`.

A public push, and a pushed tag, are visible to whoever can already see the repository once done
— for a private repo that's only its collaborators; confirm before running either regardless.

### C. PyPI (optional, a separate decision)

`pip install terrastep` (no URL, no `git+`) is lower-friction than either A or B, and is what most
people expect of a real package name — but treat it as separate from "share it with my other
projects," which A already solves completely. Needs: (B) already done, a PyPI account,
`python -m build` (produces `dist/*.whl` and `dist/*.tar.gz`), then `twine upload dist/*`. A name
squat check on PyPI for `terrastep` is worth doing before committing to the name publicly — a
published package name is hard to walk back.

## Adopting terrastep in a new repository

However the package got installed (A, B, or C), the sequence at that repo's root is the same:

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

## Maintaining terrastep as the codebase changes and new versions ship

A release is not just "bump the version number." In order:

1. **Make the actual code change** in `core.py`/`config.py`/`cli.py`/etc., with its own tests
   passing.
2. **Bump `terrastep.__version__`** in `src/terrastep/__init__.py` — the single source of truth
   (`pyproject.toml` reads it dynamically; see `CLAUDE.md`'s "Versioning and the generated
   docs/skill"). Decide the bump size using the SemVer convention above. Skip this step entirely
   for changes shared only via method A to your own other repos — there is no consumer whose
   already-passing check a local, unversioned change could silently break without you noticing,
   since it's the same person running both sides. Do bump before tagging (B) or publishing (C).
3. **Regenerate the generated docs and skill**: `venv/bin/terrastep skill build`. Not optional and
   not separable from step 2 — every generated file (`journal/terrastep_101.md`,
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
8. **Tag and push**: `git tag -a vX.Y.Z -m '<message>' && git push --follow-tags` (see method B's
   tagging note above for why `-a` and `--follow-tags` specifically), once method B is set up and
   you want one.
9. **If published to PyPI**: `python -m build`, `twine upload dist/*`.

### What a consumer does after a new version ships

- **Method A, editable install:** nothing for the CLI — it already runs this checkout's latest
  code. Still re-run `terrastep skill install --root . --force` in every consumer repo if the
  change touched the skill (`skilldoc.py`, `core.py`'s rules, `config.py`'s keys) — that copy
  never updates on its own.
- **Method A, regular install:** `pip install --force-reinstall /home/jga/dev/3p/terrastep`, then
  the same skill-install refresh if needed.
- **Method B or C:** `pip install --upgrade terrastep` (or re-pin the git tag), then the same
  skill-install refresh.
- In every case: nothing pushes an update to an already-installed skill automatically —
  `.claude/skills/terrastep/` is a snapshot from whenever it was last installed, not a live link
  to the package (not even under an editable install — see method A above). The
  `terrastep_version:` field in that repo's `SKILL.md` frontmatter is how you'd notice it's stale
  (by comparing it to `terrastep.__version__` in the newly installed package) — there is no
  automated check for this yet (Q5, 0002: recording the version was in scope; detecting a mismatch
  was explicitly deferred).
- `terrastep build && terrastep check` — confirm the upgrade didn't newly fail anything. A MAJOR
  version bump is exactly the case where it might; there's no migration tool yet, so a failure
  here means reading the release's notes and fixing documents by hand.

## What this guide does not solve

- **No automated version-mismatch detection** between an installed skill and the `terrastep`
  package that's actually running (0002, Q5). The version is recorded; nothing reads it back yet.
- **No automated migration between terrastep versions** (0001, "What this does not do"). A
  breaking rule change needs a hand-written migration note per consumer, the same shape as
  `journal/origin/handoff.md`, until that tooling exists.
- **No CI.** Every check in "Maintaining terrastep" above is run by hand, by whoever is doing the
  release. There is no automated release pipeline yet.
- **No dependency on this document for private, same-machine use.** If you only ever need method
  A, you can skip straight to "Adopting terrastep in a new repository" — everything above it in
  this file is about the day a repository stops being on this filesystem.
