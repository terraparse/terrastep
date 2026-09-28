# terrastep

## Python

- Use the local venv at `venv/` for all Python. Never use the system `python3`, `pip` or `pytest`.
  - Run the CLI: `venv/bin/terrastep <verb>` (or `venv/bin/python -m terrastep <verb>`)
  - Run tests: `venv/bin/python -m pytest -q tests`
  - Install a package: `venv/bin/pip install <package>`
- The package lives in `src/terrastep/`. Install it editable after cloning, or if `venv/` is
  rebuilt: `venv/bin/pip install -e .`. `tests/conftest.py` fails collection if `terrastep`
  resolves to anything but this repo's `src/` — a regular (non-editable) install will trip it.
- Install a package the first time you need it. Do not ask first.
- Do not commit `venv/`. `.gitignore` already lists it.
- If `venv/` is missing, recreate it with `python3 -m venv venv`, then `venv/bin/pip install -e .`
  (installs `pyyaml`, `tomli` on Python < 3.11, and the `terrastep` command) and
  `venv/bin/pip install pytest`.
- Use the scratchpad for temporary files, not `/tmp`.
