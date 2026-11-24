# CLAUDE.md

pyadtpulse is an async Python client for ADT Pulse alarm systems. It works by
scraping the Pulse web portal (`portal.adtpulse.com`) with aiohttp and lxml; ADT
has no public API. Its main consumer is the Home Assistant integration
[hass-adtpulse](https://github.com/EVWorth/hass-adtpulse), so a behavior change
here ships to Home Assistant users once that integration bumps its requirement.

## Commands

The project uses uv. `uv.lock` is gitignored, so `uv sync` resolves the newest
versions allowed by `pyproject.toml`.

```bash
uv sync                                         # create .venv with all groups
uv run --no-dev --frozen pytest --isolate       # the test suite exactly as CI runs it
uv run pytest tests/test_pulse_mfa.py           # one file (plain pytest also passes locally)
uv run ruff check                               # lint (CI: validate.yaml)
uv run ruff format --check                      # format check (CI: validate.yaml)
uv run pre-commit install                       # once per clone
```

There is no mypy and no coverage tooling. Runtime type checks come from
typeguard's `@typechecked`, which the code uses widely.

CI (`.github/workflows/`) runs the tests on Python 3.10 to 3.14, plus ruff
(`validate.yaml`) and Bandit. Code must keep working on 3.10: for example, catch
`asyncio.TimeoutError` as well as `TimeoutError`.

## Layout

- `pyadtpulse/pyadtpulse_async.py`: `PyADTPulseAsync`, the public client. The
  sync `PyADTPulse` in `__init__.py` is deprecated; don't add features to it.
- `pyadtpulse/pulse_connection.py`: login, logout, and the MFA verification-code
  flow (helpers in `pulse_mfa.py`).
- `pyadtpulse/pulse_query_manager.py`: every HTTP request goes through
  `async_query`, which handles retries, backoff and Retry-After.
- `pyadtpulse/site.py`, `zones.py`, `alarm_panel.py`, `gateway.py`: parsed
  portal state.
- `tests/data_files/`: saved portal HTML pages used as fixtures. `conftest.py`
  mocks the portal with aioresponses and with `PulseMockedWebServer`.

## Things that bite

- **Nobody can test against a live ADT account in CI**, and the maintainer
  doesn't have one. Prove portal-facing changes with saved HTML in
  `tests/data_files/` and with tests that fail without the fix. Say in the PR
  what was run against a real account, if anything.
- **ADT runs more than one portal version at once** (URLs look like
  `/myhome/31.0.0-39/...`) and can redirect a request into another version.
  Compare URLs with `PulseConnectionProperties.split_versioned_url`, never the
  full URL, and build request URLs with `make_url()` at request time.
- **The portal session cookie is `JSESSIONID`.** `PulseCookieJar` drops stale
  copies on longer paths; read its docstring before touching cookies.
- **Only one session per account works.** A second client logging in with the
  same credentials logs the first one out.
- **Test-only dependency caps** live in the `testing` group in `pyproject.toml`
  (for example `aiohttp<3.14`, because aioresponses can't mock 3.14 yet). They
  don't apply to users. Each one has a comment saying when to remove it.
- **Ruff isn't pinned** in CI, which installs the newest release. Ruff 0.17 also
  formats Python code blocks in Markdown, so `README.md` can fail the format
  check.
- **Imports are sorted by length** (`length-sort = true` in the isort config).
  Run `uv run ruff check --fix` rather than ordering them by hand.

## Workflow

- Pre-commit blocks commits to `master` (`no-commit-to-branch`), so work on a
  branch and open a PR against `master`.
- Docstrings follow the Google convention (ruff `D` rules).
- Releases: bump `version` in `pyproject.toml` in a PR, then push a tag named
  exactly `X.Y.Z` (no `v`), which runs `pypi-publish.yml`.
