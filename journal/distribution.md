# Sharing terrastep: setup and maintenance

A plain guide, not a plan: it carries no frontmatter on purpose, because it does not sit in a
designated `scan_dirs` directory (same reasoning as `terrastep_101.md`). It assumes you've read
that doc; this one is about getting terrastep *to* a project and keeping it current there, not
what terrastep checks once it's there.

terrastep is published on PyPI and backed by a public GitHub repo. This doc has three parts, in
the order a new developer needs them: how to install it, how to release a new version, and the
history of how the PyPI/GitHub setup itself was done (so the next person doesn't have to
reverse-engineer it from commit history).

## Installing terrastep

For any project that wants a released version:

```bash
pip install terrastep
```

Pin to a specific version:
```bash
pip install terrastep==0.2.0
```

Upgrade an existing install:
```bash
pip install --upgrade terrastep
```

The one thing `pip install terrastep` can't give you is code that hasn't been released yet. For
that — mainly while developing terrastep itself, or for a sibling repo on this machine that needs
an in-flight change before it's tagged — install straight from this checkout instead:
```bash
pip install -e /home/jga/dev/3p/terrastep       # live link to this working tree
pip install /home/jga/dev/3p/terrastep          # frozen snapshot of it, taken now
```
There's no version pinning this way; it's always "whatever is on disk right now." Switch back to
`pip install terrastep` once the change you needed has shipped in a release.

**In every case**, `.claude/skills/terrastep/` is a *copy* made by `terrastep skill install`, not a
live link to the installed package — not even under an editable install. Re-run it
(`terrastep skill install --force` to overwrite) in every consumer repo whenever the installed
terrastep's skill content changed. The `terrastep_version:` field in that repo's `SKILL.md`
frontmatter is how you'd notice it's gone stale — compare it to the newly installed package's
`terrastep.__version__`. Nothing checks this automatically yet (0002, Q5: recording the version was
in scope; detecting a mismatch was explicitly deferred).

## Releasing a new version (for terrastep maintainers)

A release is not just "bump the version number." In order:

1. **Make the actual code change** in `core.py`/`config.py`/`cli.py`/etc., with its own tests
   passing.
2. **Bump `terrastep.__version__`** in `src/terrastep/__init__.py` — the single source of truth
   (`pyproject.toml` reads it dynamically; see `CLAUDE.md`'s "Versioning and the generated
   docs/skill"). Use [SemVer](https://semver.org/): MAJOR for a change that could make an
   already-passing document start failing `terrastep check`, MINOR for a new verb or config key
   that doesn't change existing behavior, PATCH for a bug fix. terrastep has no automated migration
   between versions yet (0001, "What this does not do") — a MAJOR bump needs a hand-written
   migration note per consumer (the shape of `journal/origin/handoff.md`) until that tooling
   exists.
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
8. **Tag and push**: `git tag -a vX.Y.Z -m '<message>'` — an *annotated* tag; a plain `git tag
   vX.Y.Z` makes a lightweight tag with no message and no date, worth avoiding for a release
   marker — then `git push --follow-tags`, which pushes the branch and that tag together. It only
   pushes annotated tags reachable from what you're pushing, so it's safe to run routinely without
   risk of pushing some unrelated stray tag — unlike `git push --tags`, which pushes every tag in
   the repo regardless of reachability or annotation.
9. **Build the distributables**:
   ```bash
   rm -rf dist/ build/ src/terrastep.egg-info
   venv/bin/python -m build
   ```
   Produces `dist/terrastep-X.Y.Z-py3-none-any.whl` and `dist/terrastep-X.Y.Z.tar.gz`.
10. **Check them**: `venv/bin/twine check dist/*` must say `PASSED` with no warnings before
    anything is uploaded. (See "What the first build caught," below, for the two pyproject.toml
    problems this step is there to catch.)
11. **Dry run on TestPyPI first**:
    ```bash
    venv/bin/twine upload --repository testpypi dist/*
    ```
    Then actually install it — a successful upload is not the same as a working package. Use a
    scratch venv, not the project's own `venv/`:
    ```bash
    python3 -m venv /tmp/testpypi-check
    /tmp/testpypi-check/bin/pip install --index-url https://test.pypi.org/simple/ \
        --extra-index-url https://pypi.org/simple/ terrastep==X.Y.Z
    /tmp/testpypi-check/bin/python -c "import terrastep; print(terrastep.__version__)"
    cd /tmp/testpypi-check && /tmp/testpypi-check/bin/terrastep skill install
    head -5 .claude/skills/terrastep/SKILL.md     # confirm terrastep_version: X.Y.Z
    ```
    `--extra-index-url` is required: dependencies like `pyyaml` aren't published on TestPyPI, only
    on real PyPI.
12. **Upload for real**: `venv/bin/twine upload dist/*` (no `--repository`).
13. **Verify**: `pip index versions terrastep`, or visit `https://pypi.org/project/terrastep/`,
    and confirm the new version is listed.

### What a consumer does after a new version ships

- **Editable local install** (`pip install -e /home/jga/dev/3p/terrastep`): nothing for the CLI —
  it already runs this checkout's latest code. Still re-run
  `terrastep skill install --root . --force` in every consumer repo if the change touched the
  skill (`skilldoc.py`, `core.py`'s rules, `config.py`'s keys) — that copy never updates on its
  own.
- **Any other install** (PyPI, or a regular non-editable local-path install):
  `pip install --upgrade terrastep` (or `pip install --force-reinstall /home/jga/dev/3p/terrastep`
  for the local-path case), then the same skill-install refresh if needed.
- In every case, finish with `terrastep build && terrastep check` to confirm the upgrade didn't
  newly fail anything. A MAJOR version bump is exactly the case where it might; there's no
  migration tool yet, so a failure here means reading the release's notes and fixing documents by
  hand.

## How this was set up (history, for new developers)

A record of the one-time setup work, done 2026-10-01 through 2026-10-02, kept so the next person
understands how terrastep got onto GitHub and PyPI rather than having to infer it from commit
history. The commands under "Releasing a new version" above are what to actually run going
forward; this section is the story of the first time.

### GitHub remote

1. The cached `gh` GitHub auth token had gone invalid (`gh auth status` reported a bad token in the
   keyring). Fixed with `gh auth refresh -h github.com`.
2. Created the repo, public, and added it as `origin` in one step:
   ```bash
   gh repo create terraparse/terrastep --public --source=. --remote=origin \
       --description "A frontmatter and status-index standard for planning documents, plus the CLI that enforces it."
   ```
   `origin` is `https://github.com/terraparse/terrastep.git`.
3. Pushed both branches. `main` first:
   ```bash
   git push -u origin main
   ```
   `dev` needed its own `-u` push since the remote had never seen it (a plain `git push` fails for
   a branch with no upstream yet):
   ```bash
   git push -u origin dev
   ```
   After that first push, plain `git push`/`git pull` work on either branch with no flags.
4. Tagged the release and pushed the tag:
   ```bash
   git tag -a v0.2.0 -m '<message>'
   git push origin v0.2.0
   ```
   (This predates adopting `git push --follow-tags` as the standing habit — see step 8 under
   "Releasing a new version" for the command to use from now on.)

### PyPI credentials

1. Created two separate accounts — one on [pypi.org](https://pypi.org), one on
   [test.pypi.org](https://test.pypi.org) (a fully separate login; tokens are not shared between
   the two). 2FA enabled on both, since PyPI requires it.
2. Created an API token on each: Account Settings → API tokens → "Add API token." Scoped to
   "Entire account" for this first upload, since the `terrastep` project didn't exist yet on
   either index — re-scope to the project specifically after a successful upload, and delete the
   account-wide token at that point.
3. Stored both tokens in `~/.pypirc` (`chmod 600`, since it holds secrets):
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-...

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-...
   ```
4. Installed the build tooling once into the project venv: `venv/bin/pip install build twine`.

### What the first build caught

`venv/bin/python -m build` runs the build backend in an isolated environment that fetches a
current setuptools — not the one installed in this repo's `venv/` — so these only surfaced here,
not from the day-to-day `pip install -e .` used for development. Both found by
`venv/bin/twine check dist/*` and fixed before the real upload:

- `pyproject.toml` had `license = {file = "LICENSE"}` (a table) and the classifier
  `License :: OSI Approved :: MIT License`. Both are deprecated as of setuptools 77 and will stop
  being supported 2027-02-18. Replaced with the SPDX form — `license = "MIT"` plus
  `license-files = ["LICENSE"]` — and bumped `[build-system]`'s `requires` to `setuptools>=77` to
  match.
- `pyproject.toml` had no `readme` field, so `long_description` was empty — the PyPI project page
  would have rendered with no description at all. Fixed by adding `readme = "readme.md"`.
- `dist/`, the output directory `python -m build` writes to, was missing from `.gitignore` (only
  `build/` was listed). Added.

### TestPyPI dry run, then the real upload

1. `venv/bin/twine upload --repository testpypi dist/*` — succeeded, visible at
   `https://test.pypi.org/project/terrastep/0.2.0/`.
2. Installed it from TestPyPI into a scratch venv (not this repo's own `venv/`) to confirm the
   *packaged* install actually works, not just that `twine` accepted the upload — the exact
   commands are under step 11 of "Releasing a new version" above. Confirmed
   `terrastep.__version__ == "0.2.0"`, the CLI's verb list, and `terrastep skill install` producing
   a `SKILL.md` correctly stamped `terrastep_version: 0.2.0`.
3. `venv/bin/twine upload dist/*` (no `--repository`) — live at
   `https://pypi.org/project/terrastep/0.2.0/`, confirmed via `pip index versions terrastep` and
   the PyPI JSON API.

## Adopting terrastep in a new repository

Once terrastep is installed in that repo's environment (`pip install terrastep`, per above), the
sequence at that repo's root is the same regardless of how it got installed:

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

## What this guide does not solve

- **No automated version-mismatch detection** between an installed skill and the `terrastep`
  package that's actually running (0002, Q5). The version is recorded; nothing reads it back yet.
- **No automated migration between terrastep versions** (0001, "What this does not do"). A
  breaking rule change needs a hand-written migration note per consumer, the same shape as
  `journal/origin/handoff.md`, until that tooling exists.
- **No CI.** Every check in "Releasing a new version" above is run by hand, by whoever is doing the
  release. There is no automated release pipeline yet.
