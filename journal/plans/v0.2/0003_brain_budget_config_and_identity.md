---
status: planning
status_changed: 2026-09-29
type: design
next: Owner reviews Q1-Q7.
---

# Brain budget A: configuration and identity

## Summary

This is the first of four designs that build brain budget. They come from
`journal/origin/brain_budget_proposal_v2.md` ("the proposal"), section 17, doc A. The four are
0003 (this design), 0004, 0005 and 0006, in prerequisite order.

This design adds the `[brain_budget]` configuration, a `ConfigError` that exits 2, the
code-owned format definition, the two identity functions, and the read-only verb
`terrastep design budget`. It has no prerequisite. 0004 depends on it for `BudgetLimits`,
`BASE_SCHEMA`, `working_schema()` and the two identities.

After this design ships, a repository can set `enabled = true`, but no document rule reads it
yet. `terrastep check` gives the same result as today for every document.

## Scope

In scope:

- The `[brain_budget]` and `[brain_budget.limits]` tables (proposal section 8).
- `ConfigError`, and exit code 2 for it in `cli.main`.
- A new module, `src/terrastep/budget.py`, with `BASE_SCHEMA`, `FORMAT_DEFINITION`, and the
  identity functions (proposal sections 5.4 and 6).
- `terrastep design budget [--format json]` (proposal section 9.2).
- New `CONFIG_HELP` entries, and matching rows in the generated configuration table.

Not in scope: every document rule and the precheck (0004); the Complexity box, render,
scaffold, the layer inside `terrastep check`, and the `In budget` index column (0005); the
skill procedure and the 0.2.0 release (0006).

## The design

### Configuration

`config.py` gains two frozen dataclasses, and `Config` gains one field:

```python
@dataclass(frozen=True)
class BudgetLimits:
    evaluative_count: int = 10
    dependency_edge_count: int = 11
    largest_coupled_cluster_size: int = 3
    word_count: int = 2000

@dataclass(frozen=True)
class BrainBudgetConfig:
    enabled: bool = False
    max_retries: int = 2
    limits: BudgetLimits = field(default_factory=BudgetLimits)
    limits_in_file: frozenset[str] = frozenset()   # which limits terrastep.toml sets

# Config
    brain_budget: BrainBudgetConfig = field(default_factory=BrainBudgetConfig)
```

`config.load` reads the two new tables strictly. Top-level keys stay lenient, as today.

- `[brain_budget]` and `[brain_budget.limits]` must each be a table.
- An unknown key in either table raises `ConfigError`, and the message names the key.
- `enabled` must be a `bool`. `max_retries` and each limit must be an `int` of 0 or more. A
  `bool` is rejected for these, although Python treats `True` as 1.
- A missing table or key takes its default. A partial `[brain_budget.limits]` changes only the
  keys it lists. `limits_in_file` records those keys, so `design budget` can mark the others as
  defaults.

### Exit code 2

`ConfigError` is a new exception in `config.py`. `cli.main` catches it around `args.func(args)`,
prints `terrastep: configuration error: <message>` to stderr, and returns 2. Every verb that
calls `_load` therefore exits 2 on a configuration error. That includes `check`, `build` and
`hook pre-commit`.

- The pre-commit shim exits with the verb's code, so git blocks the commit.
- `integrations/claude/stop_hook.sh` treats any non-zero exit as a failure. It blocks the end of
  the turn once, and lets it end when `stop_hook_active` is true (read on 2026-09-29).

`argparse` already exits 2 for a usage error, so 2 keeps one meaning: "the command could not
start".

### Format definition and identity

`budget.py` starts with the constants and functions below. It never writes a file.

```python
BASE_SCHEMA = {...}          # proposal 5.4, without properties.schema_version
FORMAT_DEFINITION = {...}    # proposal 6.3, exactly as written

def identity(value) -> str: ...                 # proposal 6.4
def policy_id(limits: BudgetLimits) -> str:     # identity(dataclasses.asdict(limits))
def schema_version() -> str:                    # identity(FORMAT_DEFINITION)
def working_schema() -> dict:                   # BASE_SCHEMA plus
                                                # properties.schema_version = {"const": schema_version()}
```

- `policy_id` hashes the effective limits, after defaults. Writing a default in
  `terrastep.toml` and leaving it out give the same value. `enabled`, `max_retries` and
  `limits_in_file` are not hashed.
- The golden values were recomputed on 2026-09-29 with the proposal's `identity` function:
  `sha256:4a30b1da8ac7` for the default limits, `sha256:cfd3b3f6f3d5` with `word_count = 2500`,
  and `sha256:6c16c11afcf0` for `FORMAT_DEFINITION`.
- The `schema_version` value holds only if `BASE_SCHEMA["required"]` still lists
  `"schema_version"`. Only `properties.schema_version` is removed. With `required` also changed,
  the hash is `sha256:cf39dbfd0121`.
- `FORMAT_DEFINITION` names parts that 0004 and 0005 implement: the measure method IDs, the YAML
  profile, the Complexity box wording, and the draft marker. This design defines all of them, so
  the identity exists from the first commit. If 0004 or 0005 changes one, `schema_version`
  changes. No document carries a stamp before 0005, so no document goes stale.

### `terrastep design budget`

`cli.py` gains a `design` verb. This design adds only its `budget` action. 0004 adds
`precheck`, and 0005 adds `render` and `scaffold`.

The verb prints whether brain budget is on, the effective limits with defaults marked,
`max_retries`, `policy_id`, `schema_version`, and the terrastep version. It works when brain
budget is off and exits 0 then. With `--format json`:

```json
{"enabled": true, "max_retries": 2,
 "limits": {"evaluative_count": 10, "dependency_edge_count": 11,
            "largest_coupled_cluster_size": 3, "word_count": 2000},
 "defaults": ["dependency_edge_count", "evaluative_count", "largest_coupled_cluster_size"],
 "policy_id": "sha256:...", "schema_version": "sha256:...", "terrastep_version": "0.1.0"}
```

### Generated documents

`CONFIG_HELP` gains `brain_budget.enabled`, `brain_budget.max_retries` and one entry per limit.
`skilldoc._config_table` lists its rows by hand, so it gains the matching rows. `cli.py` and
`config.py` change, so `terrastep skill build` runs in the same commit (`CLAUDE.md`,
"Versioning and the generated docs/skill").

## Verification

From proposal section 14, "Configuration" and "Identity":

- The defaults apply when `[brain_budget]` is missing. A partial `[brain_budget.limits]` changes
  only what it lists.
- An unknown key, a boolean limit, a negative limit and a string limit each raise `ConfigError`.
  `terrastep check` exits 2 on each, before it reads any document.
- With `enabled = false`, every existing test gives today's result.
- `policy_id` of the defaults is `sha256:4a30b1da8ac7`. With `word_count = 2500` it is
  `sha256:cfd3b3f6f3d5`. Key order and whitespace in `terrastep.toml` do not change it. Each
  single limit change does.
- A change to any `FORMAT_DEFINITION` entry changes `schema_version`. The `const` in
  `working_schema()` equals `schema_version()`.
- `terrastep design budget` exits 0 with brain budget off and on. Its JSON has the keys above.
- A test asserts that every `CONFIG_HELP` key appears in the generated configuration table.
- The `FAILURE_CODES` registry test and the skill staleness test pass.

## Blockers

None. The proposal and the owner (2026-09-29) settled every choice here, and nothing must be
verified before coding starts. The two facts that could have blocked it were checked on
2026-09-29: the golden identities reproduce, and the Stop hook shim handles exit 2.

## Questions

### Q1 — What are the default limits?

The defaults are calibrated for software developers (proposal sections 2.9 and 4.1, I7).

**Recommendation:** `evaluative_count` 10, `dependency_edge_count` 11,
`largest_coupled_cluster_size` 3, `word_count` 2000. Each is an experiment that the pilot in
0006 tunes.

### Q2 — What can a repository configure?

A per-repository format could not appear in the shared, generated skill (I8).

**Recommendation:** only `enabled`, `max_retries` and the four limits. The ledger schema, the
Complexity box, the counting methods, the YAML rules and the draft marker are package
constants.

### Q3 — How are the identity stamps made and stored?

A hand-written label can drift from the values it names (proposal 6.1, I9, OQ7).

**Recommendation:** compute both stamps from their sources each run, as `sha256:` plus twelve
hexadecimal characters. Store them only in each design's frontmatter, never in
`terrastep.toml`. The owner decided the length on 2026-09-29.

### Q4 — What does `schema_version` cover?

A counting change re-scores documents as surely as a schema change does (proposal 6.3, I10).

**Recommendation:** the whole `FORMAT_DEFINITION`: the ledger schema, the Complexity box, the
measure method IDs, the YAML profile and the draft marker. terrastep's own design rules stay
versioned by the terrastep version.

### Q5 — Which exit codes do the verbs use?

**Recommendation:** 0 for no failures (warnings allowed), 1 for a failure or a refusal to write,
2 for a configuration or usage error (I14).

### Q6 — Is brain budget on by default?

The skill ships to every repository. A default of `true` would change how agents write designs
in repositories that never chose brain budget (I15).

**Recommendation:** `enabled = false` by default. A repository opts in.

### Q7 — How are the new names spelled?

**Recommendation:** each name follows the convention of the place where it appears (I16).
`brain_budget` in TOML, YAML and Python. `brain-budget-` as the prefix of failure codes, which
are kebab-case. No `bb-` prefix. The owner decided this on 2026-09-29 (OQ4).

## Recommendations

1. Use the default limits 10 / 11 / 3 / 2000 (Q1).
2. Configure only `enabled`, `max_retries` and the limits; the format stays in code (Q2).
3. Compute the stamps at load time, twelve hexadecimal characters, stored only in frontmatter (Q3).
4. Hash the whole format definition for `schema_version` (Q4).
5. Exit 0, 1 or 2 as above (Q5).
6. Default to `enabled = false` (Q6).
7. Name things `brain_budget` and `brain-budget-` by where they appear (Q7).

## Sequencing

1. `BudgetLimits`, `BrainBudgetConfig`, strict loading, `ConfigError`, and exit 2 in
   `cli.main`, with the configuration tests.
2. `budget.py`: `BASE_SCHEMA`, `FORMAT_DEFINITION`, the identity functions, and the golden and
   sensitivity tests.
3. The `design` verb with its `budget` action, and its tests.
4. `CONFIG_HELP` entries and the `_config_table` rows. Run `terrastep skill build`, the full test
   suite and `terrastep check` on this repository. Commit as one change.
