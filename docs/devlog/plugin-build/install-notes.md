# devflow — install & verification notes

## Verification evidence (automated, captured 2026-10-27)

**Guard test suite (sole run):**
```
$ python -m pytest tests/test_devlog_guard.py -q
...........                                                              [100%]
11 passed in 8.40s
```

**Fail-open smoke test — empty repo, no `docs/devlog/`:**
```
$ T="$(mktemp -d)"; git -C "$T" init -q
$ echo '{}' | CLAUDE_PROJECT_DIR="$T" python hooks/devlog_guard.py; echo "exit=$?"
exit=0        # no output — silent no-op, as designed
```

**Fail-open smoke test — non-object JSON stdin (the Task 2 Critical fix):**
```
$ echo 'null' | CLAUDE_PROJECT_DIR="$T" python hooks/devlog_guard.py; echo "exit=$?"
exit=0        # no output — coerced to {}, never raises
```

## Install (local marketplace)

```
/plugin marketplace add ~/Desktop/devflow-kit
/plugin install devflow@devflow-kit
```
After install, confirm the five `/devflow:*` commands and the `devflow-method` skill are listed.

> NOTE: installing globally activates the Stop-hook guard in **every** repo you open. This is safe —
> it is a silent no-op in any repo without `docs/devlog/` + a `.superpowers/sdd/progress.md` ledger
> carrying a `Devlog-dir:` line.

## Manual live verification (run once after install — needs the interactive Claude Code UI)

**Block-then-pass:**
1. In a throwaway repo: create `.superpowers/sdd/progress.md` containing
   `Devlog-dir: docs/devlog/phase1` and `Task 1: complete`; create an empty `docs/devlog/phase1/`;
   `git add -A && git commit`.
2. Try to end a turn → the Stop hook should **block** and list the missing
   `task-01-brief.md, task-01-report.md, task-01-review.md, reviews/task-01-r*.diff, tests/task-01-tests.txt`.
3. Create those five files, commit, retry → the hook should **pass**.
4. Repeat with `Task 2: complete (controller)` → only `task-02-report.md` + `task-02-review.md` required.

## Self-hosting note (devflow-kit's own repo)

devflow-kit's `.superpowers/sdd/progress.md` is a git-ignored build artifact. If you install devflow
globally and want the guard to stay quiet on devflow-kit itself, drop `.devflow/guard.json` with
`{"enabled": false}` here, or mirror the per-task trail into `docs/devlog/plugin-build/`.
