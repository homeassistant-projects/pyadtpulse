---
name: merge-prs
description: Merge one or more pyadtpulse PRs in a given order, each only once its CI is green and GitHub says it's mergeable, then check master's CI. Use when the maintainer says to merge PRs ("merge them", "merge #103 then #104", "merge when ready").
---

# Merge PRs

Only merge when the maintainer has said to, in this conversation. Use merge
commits (stacked branches and later rebases depend on it), never squash, and
never `--admin`.

## For each PR, in the order given

1. **CI is green.** `gh pr checks <n>`. Every check must be `pass`. If any is
   `pending`, check again in about a minute; the test jobs take under a minute.
   If any is `fail`, stop and report it. A first-time contributor's PR with no
   checks at all needs the maintainer to approve its workflow runs on GitHub.
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
- Report a table of PR, merge commit, and master CI result. Say plainly if a
  run hadn't finished when you last looked.

## Order

Merge in the order the maintainer gave. If none was given, merge build and CI
changes (`pyproject.toml`, `.github/`) before docs that describe them
(`CLAUDE.md`, `DEVELOPMENT.md`, `README.md`), and say which order you used.
