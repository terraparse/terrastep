"""Tests for [brain_budget] and [brain_budget.limits] in terrastep.toml (0003).

journal/plans/v0.2/0003_brain_budget_config_and_identity.md, Verification,
"Configuration": defaults apply when the table is missing; a partial
[brain_budget.limits] changes only what it lists; an unknown key, a boolean
limit, a negative limit and a string limit each raise ConfigError; with
enabled = false, every existing test gives today's result (covered by the
rest of the suite passing unchanged).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from terrastep import config as config_mod
from terrastep.config import BrainBudgetConfig, BudgetLimits, Config, ConfigError


def write(root: Path, text: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "terrastep.toml").write_text(text, encoding="utf-8")
    return root


def test_defaults_apply_when_brain_budget_is_missing(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n')
    cfg = config_mod.load(root)
    assert cfg.brain_budget == BrainBudgetConfig()
    assert cfg.brain_budget.enabled is False
    assert cfg.brain_budget.limits == BudgetLimits()
    assert cfg.brain_budget.limits_in_file == frozenset()


def test_no_config_file_gives_the_same_defaults():
    assert Config().brain_budget == BrainBudgetConfig()


def test_a_partial_limits_table_changes_only_what_it_lists(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget.limits]\nword_count = 2500\n')
    cfg = config_mod.load(root)
    assert cfg.brain_budget.limits == BudgetLimits(word_count=2500)
    assert cfg.brain_budget.limits_in_file == frozenset({"word_count"})


def test_enabled_and_max_retries_are_read(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget]\n'
                          'enabled = true\nmax_retries = 5\n')
    cfg = config_mod.load(root)
    assert cfg.brain_budget.enabled is True
    assert cfg.brain_budget.max_retries == 5


def test_every_limit_can_be_set_at_once(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget.limits]\n'
                          'evaluative_count = 4\ndependency_edge_count = 5\n'
                          'largest_coupled_cluster_size = 2\nword_count = 900\n')
    cfg = config_mod.load(root)
    assert cfg.brain_budget.limits == BudgetLimits(4, 5, 2, 900)
    assert cfg.brain_budget.limits_in_file == frozenset(
        {"evaluative_count", "dependency_edge_count", "largest_coupled_cluster_size", "word_count"})


@pytest.mark.parametrize("body", [
    '[brain_budget]\nenable = true\n',                    # unknown top-level key
    '[brain_budget.limits]\nevaluative_kount = 5\n',       # unknown limits key
])
def test_an_unknown_key_raises_config_error(tmp_path, body):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n' + body)
    with pytest.raises(ConfigError):
        config_mod.load(root)


@pytest.mark.parametrize("value", ["true", "false"])
def test_a_boolean_limit_raises_config_error(tmp_path, value):
    root = write(tmp_path, f'scan_dirs = ["journal"]\n\n[brain_budget.limits]\nword_count = {value}\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)


def test_a_negative_limit_raises_config_error(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget.limits]\nword_count = -1\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)


def test_a_string_limit_raises_config_error(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget.limits]\nword_count = "2000"\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)


def test_a_non_integer_max_retries_raises_config_error(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget]\nmax_retries = "2"\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)


def test_a_non_boolean_enabled_raises_config_error_even_when_int_like(tmp_path):
    # Python treats True as 1; an int value for `enabled` must still be rejected.
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget]\nenabled = 1\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)


def test_brain_budget_not_a_table_raises_config_error(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\nbrain_budget = "on"\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)


def test_limits_not_a_table_raises_config_error(tmp_path):
    root = write(tmp_path, 'scan_dirs = ["journal"]\n\n[brain_budget]\nlimits = "loose"\n')
    with pytest.raises(ConfigError):
        config_mod.load(root)
