"""Fails collection if `terrastep` resolves to anything but this repo's src/ (B1)."""

from pathlib import Path

import terrastep

_expected = Path(__file__).resolve().parent.parent / "src" / "terrastep"
_actual = Path(terrastep.__file__).resolve().parent
assert _actual == _expected, (
    f"terrastep imported from {_actual}, not {_expected}. "
    "Install with `pip install -e .` in this repo's venv, not a regular install."
)
