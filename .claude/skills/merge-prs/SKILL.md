---
name: merge-prs
description: Merge one or more pyadtpulse PRs in a given order, each only once its CI is green and GitHub says it's mergeable, then check master's CI. Use when the maintainer says to merge PRs ("merge them", "merge #103 then #104", "merge when ready").
---

# Merge PRs

Only merge when the maintainer has said to, in this conversation. Use merge
commits (stacked branches and later rebases depend on it), never squash, and
never `--admin`.

## For each PR, in the order given

1. **CI is green.** Wait with `gh pr checks <n> --watch --fail-fast` (run it
   in the background) and go on only if it exits 0. Don't write your own
   polling loop: a hand-rolled loop that exits on the wrong condition is how a
   PR once got merged with checks still pending. In the first few seconds
   after a push GitHub has no checks for the PR yet. `--watch` then exits 1
   with "no checks reported", so wait a few seconds and run it again. If any check is `fail`, stop
   and report it. A PR with no checks at all is either a first-time
   contributor's (the maintainer must approve its workflow runs on GitHub) or
   one whose base was just changed (see **Base branch**).
2. **GitHub has computed mergeability.** Right after another PR merges,
   `gh pr view <n> --json mergeable` returns `UNKNOWN` for a few seconds.
   Re-read it (up to about 30 seconds) until it's `MERGEABLE` or `CONFLICTING`.
   Stop on `CONFLICTING`.
3. **Merge exactly what was checked:**

   ```bash
   sha=$(gh pr view <n> --json headRefOid -q .headRefOid)
   gh pr merge <n> --merge --match-head-commit "$sha"
   ```

   `--match-head-commit` refuses the merge if someone pushed after step 1.
4. Confirm with `gh pr view <n> --json state,mergeCommit` and note the merge
   commit.

## Afterwards

- Read master's CI for the last merge commit:
  `gh run list -b master -e push -L 6`. Each master commit has its own
  concurrency group, so every merge gets a full run.
- If a merge into `master` should release (any `feat`, `fix`, `perf` or
  `refactor` commit), wait for it with `gh run watch <id> --exit-status`,
  using the id of the newest "Release and publish to PyPI" run. When several
  PRs merge back to back, only the run for master's tip releases. The older
  runs skip their bump step and pass. Then check that the release installs
  from PyPI. uv's 2-day cooldown hides a new release unless you exempt it:

  ```bash
  uv run --isolated --no-project --exclude-newer-package 'pyadtpulse=0 days' \
    --with "pyadtpulse==X.Y.Z" python -c \
    "import importlib.metadata as m, pyadtpulse; print(m.version('pyadtpulse'))"
  ```

- Report a table of PR, merge commit, and master CI result. Say plainly if a
  run hadn't finished when you last looked.

## Base branch

Merging into `master` releases automatically. A PR with a breaking commit (`!`
or `BREAKING CHANGE:`) must target `dev`, not `master`: stop and say so if one
targets `master`. Check with `gh pr view <n> --json baseRefName,commits`.
Merging into `dev` releases nothing.

Changing a PR's base (`gh pr edit <n> --base dev`) doesn't start CI, and
GitHub can keep reporting `CONFLICTING` from the old base even when the new
base is an ancestor. To fix both, close the PR and reopen it
(`gh pr close <n> && gh pr reopen <n>`). That reruns CI against the new base
and recomputes mergeability.

The `dev` -> `master` PR that publishes a major gets a merge commit like any
other. A squash would turn the `!` commits into one commit with whatever
title the squash gets, and Commitizen could miss the major.

## Order

Merge in the order the maintainer gave. If none was given, merge build and CI
changes (`pyproject.toml`, `.github/`) before docs that describe them
(`CLAUDE.md`, `DEVELOPMENT.md`, `README.md`), and say which order you used.
