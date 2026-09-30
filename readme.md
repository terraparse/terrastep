# terrastep

TerraParse Standardized Enhancement Proposals (terrastep) is a method and format by which to communicate with LLMs and agents to build better software, faster.

Full explainer: [journal/terrastep_101.md](journal/terrastep_101.md).

## The format

A YAML frontmatter block (`status`, `status_changed`, `type`, `next`, ...) on every document
inside directories you name in `terrastep.toml` (`scan_dirs`) — nowhere else in the repo is
touched. `type: plan` documents also get a body-shape check: front sections (`summary`/
`motivation`/...), then exactly `## Blockers`, `## Questions`, `## Recommendations`,
`## Sequencing` in order, with tagged, recommended items. `type: legacy` and `type: note` skip
the body check. A generated index file (`STATUS.md` by default) lists every document by status;
`terrastep check` fails if it's stale.

## Using it

```
venv/bin/pip install -e .
terrastep next-id                 # next free plan document number
# write the doc under scan_dirs, then:
terrastep check                   # 0 if clean, 1 on any rule failure
terrastep build                   # regenerate the index
terrastep install-hooks           # pre-commit hook: blocks a bad staged commit
terrastep migrate propose/apply   # bring undocumented markdown under the format
```
