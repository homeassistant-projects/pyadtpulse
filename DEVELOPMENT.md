# PyADTPulse Development Guide

Welcome! This guide explains how to set up a local development environment for contributing to pyadtpulse.

---

## 📦 Requirements

Before you start, ensure you have installed:

- Python 3.10 or newer (the version in `.python-version` is what uv installs by default)
- Git
- [`uv`](https://github.com/astral-sh/uv) 0.8 or newer
- A code editor (e.g., VSCode)

---

## 🧪 Setting Up the Development Environment with `uv`

This project uses [`uv`](https://github.com/astral-sh/uv), a fast Python package manager, to manage dependencies.

### 🔧 Installation (one-time setup)

If you don't have `uv` installed yet see the uv [installation guide](https://docs.astral.sh/uv/getting-started/installation/)

---

### 📦 Setup Python Environment

From the root of the project, run:

```bash
uv sync
uv run pre-commit install
```

`uv sync` creates the `.venv` virtual environment (or updates it) and installs the package
with the `dev` and `testing` dependency groups. `uv.lock` is not committed, so it resolves
the newest versions `pyproject.toml` allows and writes a local `uv.lock`.

`pre-commit install` makes `.git/hooks/pre-commit` run the hooks from your `.venv`: ruff
lint and format, YAML/TOML/JSON checks, and a check that blocks commits straight to
`master`. Work on a branch.

### Update vscode to use your .venv

- `ctrl + shift + p` (Command Palette)
- `Python: Select Interpreter`
- Select the environment to use. It should be `./.venv/bin/python`

---

### Running Scripts

With uv, we don't need to activate the .venv to interact with it.

- New dependencies can be added using `uv add package_name`
  (`uv add --group testing package_name` for a test-only one)
- The .venv will be used automatically when running python scripts or packages using
  `uv run ./script.py` or `uv run pytest tests`, for example

### Tests and checks

Run the tests the way CI does:

```bash
uv run --no-dev --frozen pytest --isolate
```

`--isolate` (from pytest-isolate) runs each test in its own process. HTTP responses are mocked with `aioresponses` and the HTML files in
`tests/data_files/`, so the tests never contact ADT.

Lint and format:

```bash
uv run ruff check
uv run ruff format --check
```

Ruff also formats the Python code blocks in Markdown files such as `README.md`. To run every
pre-commit hook on all files:

```bash
uv run pre-commit run --all-files
```

### Updating python versions

`.python-version` is used by uv to install the correct version of python in the .venv.
The `requires-python` field in `pyproject.toml` is used by uv to determine functioning
versions of dependencies.

If the python version needs to be updated, the exact version to use should be updated in
`.python-version`, and `pyproject.toml` should be reviewed to ensure its criteria work with
`.python-version`.

For example: if `pyproject.toml` has `requires-python = "==3.13.3"` and `.python-version`
is `3.13.4`, there will be issues.

---

## 🚀 Releasing

Releases are published to [PyPI](https://pypi.org/p/pyadtpulse) by
`.github/workflows/pypi-publish.yml` when a version tag is pushed.

1. Open a PR that bumps `version` in `pyproject.toml` and `__version__` in
   `pyadtpulse/const.py` to the new version, and moves the `Unreleased` entries in
   `CHANGELOG.md` under a heading for it. Merge it once CI passes.
2. Tag the merge commit on `master` with the version, exactly `X.Y.Z` (for example `1.2.15`,
   no `v` prefix), and push the tag:

   ```bash
   git tag 1.2.15
   git push origin 1.2.15
   ```

3. The tag push starts the workflow, which builds the package with `uv build` and uploads it
   with PyPI trusted publishing (the `pypi` environment), so no token is needed.
4. Create a GitHub release for the tag; its generated notes are the format `CHANGELOG.md`
   uses.

Only a tag that matches `X.Y.Z` triggers the workflow. It can also be started by hand from
the Actions tab, but that publishes whatever version the selected branch has.
