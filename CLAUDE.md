# terrastep

## Python

- Use the local venv at `venv/` for all Python. Never use the system `python3`, `pip` or `pytest`.
  - Run scripts: `venv/bin/python seed/scripts/<script>.py`
  - Run tests: `venv/bin/python -m pytest -q seed/tests`
  - Install a package: `venv/bin/pip install <package>`
- Install a package the first time you need it. Do not ask first.
- Do not commit `venv/`. `.gitignore` already lists it.
- If `venv/` is missing, recreate it with `python3 -m venv venv`, then install the packages the code imports
  (today: `pytest`, `pyyaml`).
- Use the scratchpad for temporary files, not `/tmp`.
