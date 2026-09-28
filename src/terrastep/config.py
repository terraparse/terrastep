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


@dataclass(frozen=True)
class MigrateConfig:
    changelog: str | None = None
    plan_dir: str | None = None


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
        migrate=MigrateConfig(changelog=migrate_data.get("changelog"), plan_dir=migrate_data.get("plan_dir")),
    )
