"""Config: finds and loads terrastep.toml. Every key has a default."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONFIG_FILENAME = "terrastep.toml"

DEFAULT_SCAN_DIRS: tuple[str, ...] = ("journal",)
DEFAULT_INDEX_FILE = "STATUS.md"
DEFAULT_EXCLUDE: tuple[str, ...] = ("CHANGELOG.md",)
DEFAULT_ID_FLOOR = 0
DEFAULT_IN_PROGRESS_CAP = 3

# [brain_budget] and [brain_budget.limits] keys. Unlike every other top-level
# terrastep.toml key, these two tables are validated strictly (0003, Q2): an
# unknown key here would otherwise have no effect and no warning.
BRAIN_BUDGET_KEYS = frozenset({"enabled", "max_retries", "limits"})
BUDGET_LIMIT_KEYS = frozenset({"evaluative_count", "dependency_edge_count",
                                "largest_coupled_cluster_size", "word_count"})


class ConfigError(Exception):
    """terrastep.toml has a [brain_budget] or [brain_budget.limits] value that
    cannot be an effective configuration: an unknown key, or a value of the
    wrong type or out of range."""

# One line per top-level terrastep.toml key, for `terrastep skill build`'s
# generated docs (0002). Defaults themselves come from the Config dataclass
# below, not duplicated here — this only supplies the description text a
# default value can't carry on its own.
CONFIG_HELP: dict[str, str] = {
    "scan_dirs": "The designated directories, and only them. A list, scanned recursively "
                 "(so version subdirectories are included). A markdown file outside every "
                 "entry is invisible to terrastep.",
    "index_file": "The generated index's filename. Always excluded from the scan. Written "
                  "inside scan_dirs[0].",
    "exclude": "Extra filenames to skip, on top of index_file.",
    "id_floor": "The next plan document's number is floor + 1.",
    "in_progress_cap": "Warning only: more than this many in-progress documents at once.",
    "aliases": "Adds heading patterns to a role; never removes a built-in one.",
    "warn_bare_section": "Warn on a `§N` reference with no document named alongside it.",
    "migrate.changelog": "A changelog file: a document it links is proposed as already "
                         "finished, dated by that line.",
    "migrate.legacy_dir": "A directory whose documents default to type: legacy during "
                        "`migrate propose`.",
    "brain_budget.enabled": "Turns on the brain budget layer for type: plan documents.",
    "brain_budget.max_retries": "Retries per plan, shared between precheck and check, for "
                                "fixing failures and for trying a different split to fit the "
                                "budget.",
    "brain_budget.limits.evaluative_count": "Blocker and question evaluation elements in the "
                                            "document, open or resolved.",
    "brain_budget.limits.dependency_edge_count": "Edges plus depends_on entries.",
    "brain_budget.limits.largest_coupled_cluster_size": "Evaluation elements in the largest "
                                                        "coupled cluster.",
    "brain_budget.limits.word_count": "Words from the H1 to the end of Sequencing, without the "
                                      "Complexity box.",
}


@dataclass(frozen=True)
class MigrateConfig:
    changelog: str | None = None
    legacy_dir: str | None = None


@dataclass(frozen=True)
class BudgetLimits:
    """The four brain budget measures and their limits (0003, proposal section 4.1)."""
    evaluative_count: int = 10
    dependency_edge_count: int = 11
    largest_coupled_cluster_size: int = 3
    word_count: int = 2000


@dataclass(frozen=True)
class BrainBudgetConfig:
    enabled: bool = False
    max_retries: int = 2
    limits: BudgetLimits = field(default_factory=BudgetLimits)
    # Which BUDGET_LIMIT_KEYS terrastep.toml actually set, so a caller (e.g.
    # `terrastep plan budget`) can mark the rest as defaults.
    limits_in_file: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Config:
    scan_dirs: tuple[str, ...] = DEFAULT_SCAN_DIRS
    index_file: str = DEFAULT_INDEX_FILE
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    id_floor: int = DEFAULT_ID_FLOOR
    in_progress_cap: int = DEFAULT_IN_PROGRESS_CAP
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    warn_bare_section: bool = False
    migrate: MigrateConfig = field(default_factory=MigrateConfig)
    brain_budget: BrainBudgetConfig = field(default_factory=BrainBudgetConfig)

    @property
    def excluded_names(self) -> frozenset[str]:
        return frozenset({self.index_file, *self.exclude})

    @property
    def index_dir(self) -> str:
        """`index_file` is always written inside the first `scan_dirs` entry (see Q7)."""
        return self.scan_dirs[0]

    @property
    def index_rel_path(self) -> str:
        return f"{self.index_dir}/{self.index_file}"


def find_config_file(start: Path) -> Path | None:
    for p in (start, *start.parents):
        candidate = p / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def find_root(start: Path | None = None) -> Path:
    """Nearest parent holding terrastep.toml, then the git root, then cwd."""
    start = (start or Path.cwd()).resolve()
    config_file = find_config_file(start)
    if config_file is not None:
        return config_file.parent
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start,
                              capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return start


def _int_ge0(value, label: str) -> int:
    # type(value) is not int, not isinstance: TOML/Python's bool is an int
    # subclass, and a boolean limit must be rejected (0003).
    if type(value) is not int or value < 0:
        raise ConfigError(f"{label} must be an integer >= 0, got {value!r}")
    return value


def _load_brain_budget(data: dict) -> BrainBudgetConfig:
    bb = data.get("brain_budget", {})
    if not isinstance(bb, dict):
        raise ConfigError("[brain_budget] must be a table")
    unknown = set(bb) - BRAIN_BUDGET_KEYS
    if unknown:
        raise ConfigError(f"[brain_budget] has unknown key(s): {sorted(unknown)}")

    enabled = bb.get("enabled", False)
    if type(enabled) is not bool:
        raise ConfigError(f"[brain_budget] enabled must be a boolean, got {enabled!r}")
    max_retries = _int_ge0(bb.get("max_retries", 2), "[brain_budget] max_retries")

    limits_data = bb.get("limits", {})
    if not isinstance(limits_data, dict):
        raise ConfigError("[brain_budget.limits] must be a table")
    unknown_limits = set(limits_data) - BUDGET_LIMIT_KEYS
    if unknown_limits:
        raise ConfigError(f"[brain_budget.limits] has unknown key(s): {sorted(unknown_limits)}")
    limit_values = {key: _int_ge0(value, f"[brain_budget.limits] {key}")
                    for key, value in limits_data.items()}

    return BrainBudgetConfig(enabled=enabled, max_retries=max_retries,
                              limits=BudgetLimits(**limit_values),
                              limits_in_file=frozenset(limit_values))


def load(root: Path, config_file: Path | None = None) -> Config:
    path = config_file if config_file is not None else (root / CONFIG_FILENAME)
    if not path.exists():
        return Config()
    with path.open("rb") as f:
        data = tomllib.load(f)

    migrate_data = data.get("migrate", {})
    return Config(
        scan_dirs=tuple(data.get("scan_dirs", DEFAULT_SCAN_DIRS)),
        index_file=data.get("index_file", DEFAULT_INDEX_FILE),
        exclude=tuple(data.get("exclude", DEFAULT_EXCLUDE)),
        id_floor=data.get("id_floor", DEFAULT_ID_FLOOR),
        in_progress_cap=data.get("in_progress_cap", DEFAULT_IN_PROGRESS_CAP),
        aliases={k: tuple(v) for k, v in data.get("aliases", {}).items()},
        warn_bare_section=data.get("warn_bare_section", False),
        migrate=MigrateConfig(changelog=migrate_data.get("changelog"),
                             legacy_dir=migrate_data.get("legacy_dir")),
        brain_budget=_load_brain_budget(data),
    )
