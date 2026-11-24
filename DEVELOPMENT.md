# PyADTPulse Development Guide

Welcome! This guide explains how to set up a local development environment for contributing to pyadtpulse.

---

## 📦 Requirements

Before you start, ensure you have installed:

- Python 3.10 or newer (the version in `.python-version` is what uv installs by default)
- Git
- [`uv`](https://github.com/astral-sh/uv) 0.9.17 or newer

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
with the `dev` and `testing` dependency groups. `uv.lock` is not committed, so `uv sync`
resolves dependencies from `pyproject.toml` and writes a local `uv.lock`. Releases newer than
2 days are skipped (`exclude-newer = "2 days"` in `[tool.uv]`). To try a brand-new release of
one package anyway:

```bash
uv lock --exclude-newer-package "NAME=0 days"
```

`pre-commit install` installs the hooks from your `.venv`: ruff lint and format, YAML/TOML/JSON
checks, a check that blocks commits straight to `master` (work on a branch), and a
commit-msg hook that rejects messages that aren't conventional commits.

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

`--isolate` (from pytest-isolate) runs each test in its own process, as CI does; plain
`uv run pytest tests` also works. HTTP responses are mocked with `aioresponses` and the HTML
files in `tests/data_files/`, so the tests never contact ADT.

Lint and format:

```bash
uv run ruff check
uv run ruff format --check
uv run deptry .   # imports vs. declared dependencies
```

Ruff also formats the Python code blocks in Markdown files such as `README.md`.

Ruff is pinned to one exact version in two places: the `dev` group in `pyproject.toml` and
the `ruff-pre-commit` `rev` in `.pre-commit-config.yaml` (CI installs the `pyproject.toml`
one). Bump both together. Dependabot opens separate pip and pre-commit PRs for each ruff
release.

To run every
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

Releases are automatic. Every push to `master` runs `.github/workflows/pypi-publish.yml`,
which runs the tests, then uses [Commitizen](https://commitizen-tools.github.io/commitizen/)
to read the commits since the last tag:

| Commit type | Release |
|---|---|
| `feat:` | minor (1.3.0 → 1.4.0) |
| `fix:`, `perf:`, `refactor:` | patch (1.3.0 → 1.3.1) |
| `BREAKING CHANGE:` footer or `!` after the type | major |
| `docs:`, `ci:`, `build:`, `chore:`, `test:`, `style:` | no release |

If there's something to release, the workflow bumps `version` in `pyproject.toml` (the only
place the version is set), adds a section to `CHANGELOG.md`, commits
`bump: version X → Y` to `master`, tags it `X.Y.Z` (no `v`), creates the GitHub release, and
publishes to PyPI with trusted publishing (the `pypi` environment). Don't edit the version
or the changelog by hand.

Because the version comes from commit messages, every commit must be a
[conventional commit](https://www.conventionalcommits.org/). The Validate workflow checks
each commit in a PR, and `uv run pre-commit install` adds a commit-msg hook that checks
locally. `uv run cz commit` writes one interactively. To preview the next release:

```bash
uv run cz bump --dry-run --yes
```

Pushing an `X.Y.Z` tag by hand still publishes that tag without a bump.
